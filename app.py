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

# --- 2. TMDB 이미지 검색 (복구 완료! 🌟) ---
def get_tmdb_image(query):
    try:
        api_key = st.secrets.get("tmdb_api_key")
        if not api_key: return "" # 키 없으면 빈칸
        
        # 영화, 드라마 통합 검색 (한국어)
        url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={query}&language=ko-KR&page=1"
        response = requests.get(url)
        data = response.json()
        
        if data['results']:
            # 포스터가 있는 첫 번째 결과 가져오기
            for item in data['results']:
                if item.get('poster_path'):
                    return f"https://image.tmdb.org/t/p/w500{item['poster_path']}"
    except:
        pass
    return ""

# --- 3. AI 분석 ---
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
    4. running_time: (중요) 이 작품의 총 러닝타임(분 단위). 영화면 영화 시간, 드라마면 '에피소드 수 x 평균 시간'으로 숫자만. (예: 120)
    5. cast_crew: 주요 감독 1명과 주연 배우 2~3명을 콤마(,)로 구분해 한국어로. (예: 봉준호, 송강호)
    
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
                with st.spinner("🧠 AI 분석 & TMDB 포스터 검색 중..."):
                    sheet = get_sheet_connection()
                    all_records = sheet.get_all_records()
                    df_existing = pd.DataFrame(all_records)
                    
                    # 중복 확인
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
                        
                        # TMDB 이미지 검색 사용
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

            st.markdown
