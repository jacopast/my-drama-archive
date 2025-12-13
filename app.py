import streamlit as st
import pandas as pd
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
from duckduckgo_search import DDGS  # 🔍 이미지 검색용 도구 추가

# --- 페이지 설정 ---
st.set_page_config(page_title="My Media Archive", page_icon="🎬", layout="wide")

# --- 1. 구글 시트 연결 ---
def get_sheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("media_db").sheet1

# --- 2. 진짜 이미지 찾기 (NEW!) ---
def search_image_url(query):
    """DuckDuckGo 검색 엔진으로 실제 이미지 주소를 가져옴"""
    try:
        with DDGS() as ddgs:
            # "제목 + 포스터"로 검색해서 첫 번째 이미지 가져오기
            results = list(ddgs.images(f"{query} 포스터", max_results=1))
            if results:
                return results[0]['image']
    except Exception as e:
        print(f"이미지 검색 실패: {e}")
    return "https://via.placeholder.com/300x450?text=No+Image" # 실패 시 대체 이미지

# --- 3. AI 분석 ---
def analyze_content(title, user_comment):
    genai.configure(api_key=st.secrets["gemini_api_key"])
    # 모델명은 최신 버전 유지
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    작품명: '{title}'
    사용자 코멘트: '{user_comment}'
    
    위 정보를 바탕으로 아래 3가지 정보를 추론해서 오직 JSON 형식으로만 답해줘. (이미지 URL은 빼고!)
    
    1. platform: Netflix, Disney+, Prime Video, Apple TV+, Watcha, TVING, Wavve, Cinema 중 가장 유력한 곳 1개. (모르면 OTT)
    2. rating: 사용자의 코멘트 뉘앙스를 분석해 1.0~5.0 사이 점수 (0.5 단위). 
    3. release_date: 이 작품의 최초 공개일 (YYYY-MM-DD). 검색해서 정확히 찾아줘.
    
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
    st.markdown("##### 툭 던지면, 척 쌓입니다.")
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            input_title = st.text_input("작품명", placeholder="예: 자백의 대가")
            input_comment = st.text_input("한 줄 평", placeholder="예: 김고은 연기 미쳤다")
        with col2:
            input_date = st.date_input("본 날짜 (선택)", value=None, help="비워두면 개봉일로 기록됨")
            
        submitted = st.form_submit_button("기록 저장 💾")

        if submitted:
            if not input_title or not input_comment:
                st.warning("작품명과 한 줄 평은 필수입니다!")
            else:
                with st.spinner("🔍 포스터를 검색하고 정보를 분석 중..."):
                    # 1. AI로 텍스트 정보 분석
                    ai_data = analyze_content(input_title, input_comment)
                    
                    # 2. 검색 엔진으로 실제 이미지 찾기 (여기가 핵심!)
                    real_image_url = search_image_url(input_title)
                    
                    if ai_data:
                        if input_date:
                            final_date = input_date.strftime("%Y-%m-%d")
                        else:
                            final_date = ai_data.get('release_date', datetime.now().strftime("%Y-%m-%d"))

                        try:
                            sheet = get_sheet_connection()
                            row_data = [
                                final_date,
                                input_title,
                                ai_data['platform'],
                                ai_data['rating'],
                                input_comment,
                                ai_data['release_date'],
                                real_image_url  # 진짜 찾은 이미지 주소 넣기
                            ]
                            sheet.append_row(row_data)
                            
                            # 저장 성공 메시지와 함께 찾은 이미지 보여주기
                            st.success(f"**[{input_title}]** 저장 완료!")
                            st.image(real_image_url, width=200, caption="검색된 포스터")
                            
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
            
            # 갤러리 스타일 (최신순)
            st.markdown("### 🗂️ Recent Log")
            df = df.sort_values(by="Date", ascending=False)
            
            for idx, row in df.iterrows():
                with st.container():
                    c_img, c_txt = st.columns([1, 4])
                    with c_img:
                        try:
                            st.image(row['Image'], use_container_width=True)
                        except:
                            st.error("이미지 로딩 실패")
                    with c_txt:
                        st.subheader(f"{row['Title']} (★{row['Rating']})")
                        st.caption(f"{row['Date']} 시청 | {row['Platform']} | {row['ReleaseDate']} 개봉")
                        st.info(f"🗣️ {row['Comment']}")
                    st.divider()
        else:
            st.info("데이터가 없습니다.")

    except Exception as e:
        st.error(f"데이터 로딩 오류: {e}")
