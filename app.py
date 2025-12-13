import streamlit as st
import pandas as pd
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# --- 페이지 설정 ---
st.set_page_config(page_title="My Media Archive", page_icon="🎬", layout="wide")

# --- 1. 구글 시트 & AI 연결 함수 ---
def get_sheet_connection():
    # Streamlit의 비밀 공간(Secrets)에서 키를 가져옴
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # secrets.toml 파일 구조에 맞춰서 dict로 변환
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("media_db").sheet1  # 시트 이름 'media_db' 필수!

def analyze_content(title, user_comment):
    # Gemini AI에게 정보 추론 시키기
    genai.configure(api_key=st.secrets["gemini_api_key"])
    model = genai.GenerativeModel("gemini-pro")
    
    prompt = f"""
    작품명: '{title}'
    사용자 코멘트: '{user_comment}'
    
    위 정보를 바탕으로 아래 4가지 정보를 추론해서 오직 JSON 형식으로만 답해줘. (다른 말 하지마)
    
    1. platform: Netflix, Disney+, Prime Video, Apple TV+, Watcha, TVING, Wavve, Cinema 중 가장 유력한 곳 1개. (모르면 OTT)
    2. rating: 사용자의 코멘트 뉘앙스를 분석해 1.0~5.0 사이 점수 (0.5 단위). 
       - 부정적/욕설/실망/하차/별로/어휴 -> 1.0 ~ 2.5
       - 보통/킬링타임/볼만함 -> 3.0 ~ 3.5
       - 추천/좋음/수작/재밌음 -> 4.0 ~ 4.5
       - 인생작/최고/미쳤다/압도적 -> 5.0
    3. release_date: 이 작품의 최초 공개일 (YYYY-MM-DD). 검색해서 정확히 찾아줘.
    4. image_url: 이 작품의 공식 포스터 이미지 URL (구글 검색 최상단 결과).
    
    JSON 예시:
    {{
        "platform": "Netflix",
        "rating": 4.5,
        "release_date": "2025-01-01",
        "image_url": "https://image.tmdb.org/..."
    }}
    """
    try:
        response = model.generate_content(prompt)
        # JSON 부분만 발라내기
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        st.error(f"AI 분석 실패: {e}")
        return None

# --- 2. 화면 구성 (UI) ---
st.title("🎬 Yoon's Media Archive")

# 탭 구성
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
                with st.spinner("🤖 AI가 정보를 찾고 있습니다..."):
                    ai_data = analyze_content(input_title, input_comment)
                    
                    if ai_data:
                        # 날짜 로직: 입력값 없으면 개봉일 사용
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
                                ai_data['image_url']
                            ]
                            sheet.append_row(row_data)
                            st.success(f"**[{input_title}]** 저장 완료! (★{ai_data['rating']} / {ai_data['platform']})")
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
            # 상단 요약
            c1, c2, c3 = st.columns(3)
            c1.metric("총 감상", f"{len(df)}편")
            c2.metric("평균 별점", f"★ {df['Rating'].mean():.1f}")
            best_movie = df.loc[df['Rating'].idxmax()]
            c3.metric("최고 평점", f"{best_movie['Title']}")
            
            st.divider()
            
            # 갤러리 뷰 (최신순)
            st.markdown("### 🗂️ Recent Log")
            df = df.sort_values(by="Date", ascending=False)
            
            for idx, row in df.iterrows():
                with st.container():
                    c_img, c_txt = st.columns([1, 4])
                    with c_img:
                        try:
                            st.image(row['Image'], use_container_width=True)
                        except:
                            st.write("No Image")
                    with c_txt:
                        st.subheader(f"{row['Title']} (★{row['Rating']})")
                        st.caption(f"{row['Date']} 시청 | {row['Platform']} | {row['ReleaseDate']} 개봉")
                        st.info(f"🗣️ {row['Comment']}")
                    st.divider()
        else:
            st.info("아직 데이터가 없습니다. 첫 기록을 남겨보세요!")

    except Exception as e:
        st.error("데이터를 불러올 수 없습니다. (설정 확인 필요)")
