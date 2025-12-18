import streamlit as st
import pandas as pd
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import requests

# --- 페이지 설정 ---
st.set_page_config(page_title="My Media Archive", page_icon="🎬", layout="wide")

# --- 1. 구글 시트 연결 ---
def get_sheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("media_db").sheet1

# --- 2. 애플(iTunes) 이미지 검색 (키 필요 없음) ---
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

# --- 3. AI 분석 (내용을 합쳐서 새로 분석할 수 있게 함) ---
def analyze_content(title, combined_comment):
    genai.configure(api_key=st.secrets["gemini_api_key"])
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    작품명: '{title}'
    누적 코멘트: '{combined_comment}'
    
    위의 모든 코멘트 내용을 종합해서 JSON 형식으로만 답해줘.
    
    1. platform: Netflix, Disney+, Prime Video, Apple TV+, Watcha, TVING, Wavve, Cinema 중 1개.
    2. rating: 전체 코멘트의 뉘앙스를 종합해 1.0~5.0 사이 점수 (0.5 단위).
    3. release_date: 최초 공개일 (YYYY-MM-DD).
    
    JSON 예시:
    {{
        "platform": "Netflix",
        "rating": 4.5,
        "release_date": "2025-01-01"
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

tab1, tab2 = st.tabs(["📝 기록하기", "📊 통계/히스토리"])

with tab1:
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            input_title = st.text_input("작품명", placeholder="예: 얄미운 사랑")
            input_comment = st.text_input("새로운 한 줄 평", placeholder="예: 12화부터 지루함")
        with col2:
            input_date = st.date_input("본 날짜 (선택)", value=None)
            
        submitted = st.form_submit_button("기록 저장 💾")

        if submitted:
            if not input_title or not input_comment:
                st.warning("작품명과 코멘트를 입력하세요.")
            else:
                with st.spinner("🔄 데이터 확인 및 AI 분석 중..."):
                    sheet = get_sheet_connection()
                    all_records = sheet.get_all_records()
                    df_existing = pd.DataFrame(all_records)
                    
                    # 중복 확인 (제목 기준)
                    existing_row_index = -1
                    combined_comment = input_comment
                    
                    if not df_existing.empty and input_title in df_existing['Title'].values:
                        # 이미 있는 경우: 기존 데이터 찾기
                        idx = df_existing[df_existing['Title'] == input_title].index[0]
                        existing_row_index = idx + 2 # 헤더(1) + 0부터 시작하는 인덱스(1) = +2
                        old_comment = df_existing.iloc[idx]['Comment']
                        combined_comment = f"{old_comment} / {input_comment}"
                        st.info(f"📍 기존 기록을 발견했습니다! 내용을 합쳐서 업데이트합니다.")

                    # AI 분석 (합쳐진 코멘트로 점수 재산정)
                    ai_data = analyze_content(input_title, combined_comment)
                    
                    if ai_data:
                        final_date = input_date.strftime("%Y-%m-%d") if input_date else ai_data.get('release_date', datetime.now().strftime("%Y-%m-%d"))
                        real_image_url = get_itunes_image(input_title)
                        
                        row_data = [
                            final_date,
                            input_title,
                            ai_data['platform'],
                            ai_data['rating'],
                            combined_comment,
                            ai_data['release_date'],
                            real_image_url
                        ]

                        try:
                            if existing_row_index > 0:
                                # 기존 행 업데이트 (A열부터 G열까지)
                                sheet.update(f"A{existing_row_index}:G{existing_row_index}", [row_data])
                                st.success(f"**[{input_title}]** 업데이트 완료! (점수: {ai_data['rating']})")
                            else:
                                # 새 행 추가
                                sheet.append_row(row_data)
                                st.success(f"**[{input_title}]** 신규 저장 완료!")
                            
                            if real_image_url:
                                st.image(real_image_url, width=150)
                        except Exception as e:
                            st.error(f"저장 실패: {e}")

# [탭 2] 통계 화면 (기존과 동일)
with tab2:
    if st.button("새로고침 🔄"):
        st.rerun()
    try:
        sheet = get_sheet_connection()
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("총 감상", f"{len(df)}편")
            c2.metric("평균 별점", f"★ {df['Rating'].mean():.1f}")
            try:
                best_movie = df.loc[df['Rating'].idxmax()]
                c3.metric("최고 평점", f"{best_movie['Title']}")
            except: pass
            st.divider()
            df = df.sort_values(by="Date", ascending=False)
            for idx, row in df.iterrows():
                with st.container():
                    c_img, c_txt = st.columns([1, 4])
                    with c_img:
                        if row['Image'] and str(row['Image']).startswith('http'):
                            st.image(row['Image'], width=100)
                        else: st.markdown("## 🎬")
                    with c_txt:
                        st.subheader(f"{row['Title']} (★{row['Rating']})")
                        st.caption(f"{row['Date']} | {row['Platform']}")
                        st.info(f"🗣️ {row['Comment']}")
                    st.divider()
        else: st.info("데이터가 없습니다.")
    except Exception as e: st.error(f"로딩 오류: {e}")
