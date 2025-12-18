import streamlit as st
import pandas as pd
from google import genai # 최신 라이브러리 사용
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import requests
from collections import Counter

# --- 페이지 설정 ---
st.set_page_config(page_title="My Media Archive", page_icon="🎬", layout="wide")

# --- 유틸리티: 별점 예쁘게 보여주기 ---
def get_star_string(rating):
    try:
        score = float(rating)
        full_stars = int(score)
        has_half = (score - full_stars) >= 0.5
        return "⭐" * full_stars + ("½" if has_half else "")
    except:
        return str(rating)

# --- 1. 구글 시트 연결 ---
def get_sheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("media_db").sheet1

# --- 2. TMDB 이미지 검색 ---
def get_tmdb_image(query):
    try:
        api_key = st.secrets.get("tmdb_api_key")
        if not api_key: return ""
        
        url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={query}&language=ko-KR&page=1"
        response = requests.get(url)
        data = response.json()
        
        if data['results']:
            for item in data['results']:
                if item.get('poster_path'):
                    return f"https://image.tmdb.org/t/p/w500{item['poster_path']}"
    except:
        pass
    return ""

# --- 3. AI 분석 (안정적인 1.5 Flash 모델 사용 🟢) ---
def analyze_content(title, combined_comment):
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    
    prompt = f"""
    작품명: '{title}'
    누적 코멘트: '{combined_comment}'
    
    위 정보를 바탕으로 JSON 형식으로만 답해줘.
    
    1. platform: Netflix, Disney+, Prime Video, Apple TV+, Watcha, TVING, Wavve, Cinema 중 1개.
    2. rating: 전체 뉘앙스 분석하여 1.0~5.0 사이 점수 (0.5 단위).
    3. release_date: 최초 공개일 (YYYY-MM-DD).
    4. running_time: 총 러닝타임(분 단위). 숫자만.
    5. cast_crew: 주요 감독 1명과 주연 배우 2~3명을 콤마(,)로 구분해 한국어로. (예: 봉준호(연출), 송강호)
    
    JSON 예시:
    {{
        "platform": "Netflix",
        "rating": 4.5,
        "release_date": "2025-01-01",
        "running_time": 130,
        "cast_crew": "이응복(연출), 김고은, 공유"
    }}
    """
    try:
        # 여기가 변경되었습니다: gemini-2.0 -> gemini-1.5-flash
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        # 에러가 나면 화면에 보여줌
        st.error(f"AI 분석 실패: {e}")
        return None

# --- 4. 화면 구성 ---
st.title("🎬 Yoon's Media Archive")

tab1, tab2 = st.tabs(["📝 기록하기", "📊 인사이트/통계"])

# [탭 1] 입력 및 업데이트
with tab1:
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            input_title = st.text_input("작품명", placeholder="예: 오징어 게임 2")
            input_comment = st.text_input("코멘트", placeholder="예: 이정재 연기가 좀 달라졌네")
        with col2:
            input_date = st.date_input("본 날짜 (선택)", value=None)
            
        submitted = st.form_submit_button("기록 저장 💾")

        if submitted:
            if not input_title or not input_comment:
                st.warning("내용을 입력해주세요.")
            else:
                with st.spinner("🧠 AI 분석 & TMDB 포스터 검색 중..."):
                    sheet = get_sheet_connection()
                    all_records = sheet.get_all_records()
                    df_existing = pd.DataFrame(all_records)
                    
                    existing_row_index = -1
                    combined_comment = input_comment
                    
                    if not df_existing.empty and input_title in df_existing['Title'].values:
                        idx = df_existing[df_existing['Title'] == input_title].index[0]
                        existing_row_index = idx + 2 
                        old_comment = df_existing.iloc[idx]['Comment']
                        combined_comment = f"{old_comment} / {input_comment}"
                        st.info(f"📍 내용을 합쳐서 업데이트합니다.")

                    ai_data = analyze_content(input_title, combined_comment)
                    
                    if ai_data:
                        final_date = input_date.strftime("%Y-%m-%d") if input_date else ai_data.get('release_date', datetime.now().strftime("%Y-%m-%d"))
                        
                        real_image_url = get_tmdb_image(input_title)
                        
                        row_data = [
                            final_date,
                            input_title,
                            ai_data['platform'],
                            ai_data['rating'],
                            combined_comment,
                            ai_data['release_date'],
                            real_image_url,
                            ai_data.get('running_time', 0),
                            ai_data.get('cast_crew', '')
                        ]

                        try:
                            if existing_row_index > 0:
                                sheet.update(f"A{existing_row_index}:I{existing_row_index}", [row_data])
                                st.success(f"업데이트 완료! ({get_star_string(ai_data['rating'])})")
                            else:
                                sheet.append_row(row_data)
                                st.success(f"저장 완료! ({get_star_string(ai_data['rating'])})")
                            
                            if real_image_url:
                                st.image(real_image_url, width=150)
                        except Exception as e:
                            st.error(f"저장 실패: {e}")

# [탭 2] 통계
with tab2:
    if st.button("새로고침 🔄"): st.rerun()
    try:
        sheet = get_sheet_connection()
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
            if 'RunningTime' not in df.columns: df['RunningTime'] = 0
            if 'CastCrew' not in df.columns: df['CastCrew'] = ""
            df['RunningTime'] = pd.to_numeric(df['RunningTime'], errors='coerce').fillna(0)

            st.markdown("### 📊 Dashboard")
            filter_option = st.radio("기간 선택", ["전체 누적", "올해 (2025)"], horizontal=True)
            target_df = df[df['Date'].dt.year == datetime.now().year] if filter_option == "올해 (2025)" else df

            if not target_df.empty:
                total_min = target_df['RunningTime'].sum()
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("총 편수", f"{len(target_df)}편")
                m2.metric("총 시간", f"{int(total_min//60)}시간 {int(total_min%60)}분")
                m3.metric("평균 별점", f"{target_df['Rating'].mean():.1f}")
                best = target_df.loc[target_df['Rating'].idxmax()]
                m4.metric("최고작", f"{best['Title']}")
                
                st.divider()
                st.subheader("🏆 믿고 보는 제작진 (My Favorites)")
                high_rated_df = target_df[target_df['Rating'] >= 4.0]
                all_names = [name.strip() for names in high_rated_df['CastCrew'] for name in names.split(',') if name]
                if all_names:
                    counts = Counter(all_names).most_common(7)
                    cols = st.columns(len(counts))
                    for i, (n, c) in enumerate(counts):
                        cols[i].markdown(f"**{i+1}위**\n\n{n} ({c}회)")
                
                st.divider()
                st.subheader("📝 Review Log")
                target_df = target_df.sort_values(by="Date", ascending=False)
                for i, r in target_df.iterrows():
                    with st.container():
                        c1, c2 = st.columns([1, 4])
                        if r['Image'] and str(r['Image']).startswith('http'): c1.image(r['Image'], width=100)
                        else: c1.markdown("## 🎬")
                        c2.markdown(f"#### {r['Title']} <span style='color:orange'>{get_star_string(r['Rating'])}</span>", unsafe_allow_html=True)
                        c2.caption(f"{r['Date'].strftime('%Y-%m-%d')} | {r['Platform']} | ⏳ {int(r['RunningTime'])}분 | {r['CastCrew']}")
                        c2.write(f"🗣️ {r['Comment']}")
                    st.divider()
            else: st.warning("데이터가 없습니다.")
        else: st.info("데이터가 없습니다.")
    except Exception as e: st.error(f"오류: {e}")
