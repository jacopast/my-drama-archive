import streamlit as st
import pandas as pd
import google.generativeai as genai
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

# --- 2. 애플(iTunes) 이미지 검색 ---
def get_itunes_image(query):
    try:
        url = f"https://itunes.apple.com/search?term={query}&country=KR&media=all&limit=1"
        response = requests.get(url)
        data = response.json()
        if data['resultCount'] > 0:
            artwork = data['results'][0].get('artworkUrl100')
            return artwork.replace('100x100bb', '600x600bb') 
    except:
        pass
    return ""

# --- 3. AI 분석 (배우, 러닝타임 추가) ---
def analyze_content(title, combined_comment):
    genai.configure(api_key=st.secrets["gemini_api_key"])
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    작품명: '{title}'
    누적 코멘트: '{combined_comment}'
    
    위 정보를 바탕으로 JSON 형식으로만 답해줘.
    
    1. platform: Netflix, Disney+, Prime Video, Apple TV+, Watcha, TVING, Wavve, Cinema 중 1개.
    2. rating: 전체 뉘앙스 분석하여 1.0~5.0 사이 점수 (0.5 단위).
    3. release_date: 최초 공개일 (YYYY-MM-DD).
    4. running_time: (중요) 이 작품의 총 러닝타임(분 단위). 영화면 영화 시간, 드라마면 '에피소드 수 x 평균 시간'으로 계산해서 숫자만 적어. (예: 120)
    5. cast_crew: 주요 감독 1명과 주연 배우 2~3명의 이름을 콤마(,)로 구분해서 한국어로 적어줘. (예: 봉준호, 송강호, 이선균)
    
    JSON 예시:
    {{
        "platform": "Netflix",
        "rating": 4.5,
        "release_date": "2025-01-01",
        "running_time": 130,
        "cast_crew": "이응복, 김고은, 공유"
    }}
    """
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
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
                with st.spinner("🧠 AI가 분석하고 배우와 시간을 계산 중..."):
                    sheet = get_sheet_connection()
                    all_records = sheet.get_all_records()
                    df_existing = pd.DataFrame(all_records)
                    
                    # 중복 확인 로직
                    existing_row_index = -1
                    combined_comment = input_comment
                    
                    if not df_existing.empty and input_title in df_existing['Title'].values:
                        idx = df_existing[df_existing['Title'] == input_title].index[0]
                        existing_row_index = idx + 2 
                        old_comment = df_existing.iloc[idx]['Comment']
                        combined_comment = f"{old_comment} / {input_comment}"
                        st.info(f"📍 기존 기록 발견! 내용을 합칩니다.")

                    ai_data = analyze_content(input_title, combined_comment)
                    
                    if ai_data:
                        final_date = input_date.strftime("%Y-%m-%d") if input_date else ai_data.get('release_date', datetime.now().strftime("%Y-%m-%d"))
                        real_image_url = get_itunes_image(input_title)
                        
                        # 저장할 데이터 (9개 컬럼)
                        row_data = [
                            final_date,
                            input_title,
                            ai_data['platform'],
                            ai_data['rating'],
                            combined_comment,
                            ai_data['release_date'],
                            real_image_url,
                            ai_data.get('running_time', 0), # 8열: 시간
                            ai_data.get('cast_crew', '')    # 9열: 배우
                        ]

                        try:
                            # 구글 시트 범위 업데이트 (A~I열)
                            if existing_row_index > 0:
                                sheet.update(f"A{existing_row_index}:I{existing_row_index}", [row_data])
                                st.success(f"[{input_title}] 업데이트 완료! ({get_star_string(ai_data['rating'])})")
                            else:
                                sheet.append_row(row_data)
                                st.success(f"[{input_title}] 저장 완료! ({get_star_string(ai_data['rating'])})")
                            
                            if real_image_url:
                                st.image(real_image_url, width=150)
                        except Exception as e:
                            st.error(f"저장 실패: {e}")

# [탭 2] 통계 및 "보이면 본다" 리스트
with tab2:
    if st.button("새로고침 🔄"):
        st.rerun()
        
    try:
        sheet = get_sheet_connection()
        records = sheet.get_all_records()
        df = pd.DataFrame(records)

        if not df.empty:
            # 데이터 전처리
            df['Date'] = pd.to_datetime(df['Date'])
            df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
            
            # 새로 추가된 컬럼이 옛날 데이터엔 없을 수 있으므로 처리
            if 'RunningTime' not in df.columns: df['RunningTime'] = 0
            if 'CastCrew' not in df.columns: df['CastCrew'] = ""
            df['RunningTime'] = pd.to_numeric(df['RunningTime'], errors='coerce').fillna(0)

            # 필터링 (전체 vs 올해)
            st.markdown("### 📊 Dashboard")
            filter_option = st.radio("기간 선택", ["전체 누적", "올해 (2025)"], horizontal=True)
            
            if filter_option == "올해 (2025)":
                target_df = df[df['Date'].dt.year == datetime.now().year]
            else:
                target_df = df

            if not target_df.empty:
                # 1. 숫자 통계
                total_min = target_df['RunningTime'].sum()
                hours = int(total_min // 60)
                mins = int(total_min % 60)
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("총 감상 편수", f"{len(target_df)}편")
                m2.metric("총 투자 시간", f"{hours}시간 {mins}분")
                m3.metric("평균 별점", f"{target_df['Rating'].mean():.1f}점")
                
                best_row = target_df.loc[target_df['Rating'].idxmax()]
                worst_row = target_df.loc[target_df['Rating'].idxmin()]
                m4.metric("최고 / 최저", f"🔼 {best_row['Title']} / 🔽 {worst_row['Title']}")

                st.divider()

                # 2. "보이면 본다" 리스트 (배우/감독 분석)
                st.subheader("🏆 믿고 보는 제작진/배우 (My Favorites)")
                st.caption("평점 4.0 이상 준 작품에 출연한 배우/감독들의 등장 횟수입니다.")
                
                # 평점 4.0 이상인 작품만 골라내기
                high_rated_df = target_df[target_df['Rating'] >= 4.0]
                
                all_names = []
                for names in high_rated_df['CastCrew']:
                    if names:
                        # 콤마로 쪼개고 공백 제거해서 리스트에 담기
                        splitted = [x.strip() for x in names.split(',')]
                        all_names.extend(splitted)
                
                if all_names:
                    # 빈도수 계산
                    counts = Counter(all_names).most_common(7) # TOP 7
                    
                    # 가로로 배치
                    cols = st.columns(len(counts))
                    for idx, (name, count) in enumerate(counts):
                        with cols[idx]:
                            st.markdown(f"**{idx+1}위**")
                            st.info(f"**{name}**\n\n({count}회)")
                else:
                    st.info("아직 4.0점 이상 준 작품이 충분하지 않아요.")

                st.divider()
                
                # 3. 갤러리 리스트
                st.subheader("📝 Review Log")
                # 최신순 정렬
                target_df = target_df.sort_values(by="Date", ascending=False)
                
                for idx, row in target_df.iterrows():
                    with st.container():
                        c_img, c_txt = st.columns([1, 4])
                        with c_img:
                            if row['Image'] and str(row['Image']).startswith('http'):
                                st.image(row['Image'], width=100)
                            else: st.markdown("## 🎬")
                        with c_txt:
                            # 별점 표시 함수 적용
                            stars = get_star_string(row['Rating'])
                            st.markdown(f"#### {row['Title']} <span style='color:orange'>{stars}</span>", unsafe_allow_html=True)
                            
                            # 메타 정보 (러닝타임, 배우 등)
                            meta_info = f"{row['Date'].strftime('%Y-%m-%d')} | {row['Platform']} | ⏳ {int(row['RunningTime'])}분"
                            if row['CastCrew']:
                                meta_info += f" | 👥 {row['CastCrew']}"
                            st.caption(meta_info)
                            
                            st.write(f"🗣️ {row['Comment']}")
                        st.divider()
            else:
                st.warning("선택한 기간에 데이터가 없습니다.")
        else:
            st.info("데이터가 없습니다.")
    except Exception as e:
        st.error(f"로딩 오류: {e}")
