import streamlit as st
import pandas as pd
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import requests # 통신 도구

# --- 페이지 설정 ---
st.set_page_config(page_title="My Media Archive", page_icon="🎬", layout="wide")

# --- 1. 구글 시트 연결 ---
def get_sheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("media_db").sheet1

# --- 2. TMDB 이미지 찾기 (디버깅 모드 🚨) ---
def get_tmdb_image(query):
    try:
        # 1. 키 확인
        api_key = st.secrets.get("tmdb_api_key")
        if not api_key:
            st.error("🚨 TMDB 키가 Secrets에 없습니다!")
            return ""
            
        # 2. 검색 요청
        url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={query}&language=ko-KR&page=1"
        response = requests.get(url)
        
        # 3. 응답 코드 확인 (200이 아니면 에러)
        if response.status_code != 200:
            st.error(f"🚨 TMDB 연결 실패! 상태 코드: {response.status_code}")
            st.write(response.text) # 에러 내용 보여주기
            return ""

        data = response.json()
        
        if data['results']:
            poster_path = data['results'][0].get('poster_path')
            if poster_path:
                return f"https://image.tmdb.org/t/p/w500{poster_path}"
            else:
                st.warning(f"검색은 됐는데 포스터가 없네요. (검색어: {query})")
        else:
            st.warning(f"TMDB에서 검색 결과가 없습니다. (검색어: {query})")
            
    except Exception as e:
        st.error(f"🚨 이미지 검색 중 에러 발생: {e}")
    
    return ""

# --- 3. AI 분석 ---
def analyze_content(title, user_comment):
    genai.configure(api_key=st.secrets["gemini_api_key"])
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    작품명: '{title}'
    사용자 코멘트: '{user_comment}'
    
    위 정보를 바탕으로 JSON 형식으로만 답해줘.
    
    1. platform: Netflix, Disney+, Prime Video, Apple TV+, Watcha, TVING, Wavve, Cinema 중 1개.
    2. rating: 1.0~5.0 사이 점수 (0.5 단위).
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

# [탭 1] 입력 화면
with tab1:
    with st.form("entry_form", clear_on_submit=False): # 디버깅 위해 자동지움 끔
        col1, col2 = st.columns([3, 1])
        with col1:
            input_title = st.text_input("작품명", placeholder="예: 오징어 게임")
            input_comment = st.text_input("한 줄 평", placeholder="예: 3편이 제일 재밌네")
        with col2:
            input_date = st.date_input("본 날짜 (선택)", value=None)
            
        submitted = st.form_submit_button("테스트 저장 💾")

        if submitted:
            if not input_title:
                st.warning("작품명을 입력하세요.")
            else:
                with st.spinner("🔍 분석 중..."):
                    # 1. AI 분석
                    ai_data = analyze_content(input_title, input_comment)
                    
                    # 2. TMDB 이미지 검색 (에러나면 화면에 뜸)
                    real_image_url = get_tmdb_image(input_title)
                    
                    if ai_data:
                        if input_date:
                            final_date = input_date.strftime("%Y-%m-%d")
                        else:
                            final_date = ai_data.get('release_date', datetime.now().strftime("%Y-%m-%d"))

                        # 구글 시트 저장
                        try:
                            sheet = get_sheet_connection()
                            row_data = [
                                final_date,
                                input_title,
                                ai_data['platform'],
                                ai_data['rating'],
                                input_comment,
                                ai_data['release_date'],
                                real_image_url
                            ]
                            sheet.append_row(row_data)
                            
                            st.success(f"**[{input_title}]** 저장 완료!")
                            
                            if real_image_url:
                                st.image(real_image_url, width=150, caption="성공!")
                            else:
                                st.error("이미지를 못 가져왔습니다. 위 에러 메시지를 확인하세요.")
                                
                        except Exception as e:
                            st.error(f"구글 시트 저장 실패: {e}")

# [탭 2] 통계 화면
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
            except:
                pass
            
            st.divider()
            
            # 갤러리 뷰
            st.markdown("### 🗂️ Recent Log")
            df = df.sort_values(by="Date", ascending=False)
            
            for idx, row in df.iterrows():
                with st.container():
                    c_img, c_txt = st.columns([1, 4])
                    with c_img:
                        if row['Image'] and str(row['Image']).startswith('http'):
                            st.image(row['Image'], width=100)
                        else:
                            st.markdown("## 🎬")
                    with c_txt:
                        st.subheader(f"{row['Title']} (★{row['Rating']})")
                        st.caption(f"{row['Date']} 시청 | {row['Platform']} | {row['ReleaseDate']} 개봉")
                        st.info(f"🗣️ {row['Comment']}")
                    st.divider()
        else:
            st.info("데이터가 없습니다.")

    except Exception as e:
        st.error(f"데이터 로딩 오류: {e}")
