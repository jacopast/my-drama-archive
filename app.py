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

# --- 3. AI 분석 (역할 표기 로직 추가) ---
def analyze_content(title, combined_comment):
    genai.configure(api_key=st.secrets["gemini_api_key"])
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # 프롬프트 수정: 스태프는 (역할) 표기, 배우는 이름만
    prompt = f"""
    작품명: '{title}'
    누적 코멘트: '{combined_comment}'
    
    위 정보를 바탕으로 JSON 형식으로만 답해줘.
    
    1. platform: Netflix, Disney+, Prime Video, Apple TV+, Watcha, TVING, Wavve, Cinema 중 1개.
    2. rating: 전체 뉘앙스 분석하여 1.0~5.0 사이 점수 (0.5 단위).
    3. release_date: 최초 공개일 (YYYY-MM-DD).
    4. running_time: 총 러닝타임(분 단위). 숫자만.
    5. cast_crew: 
       - 주요 스태프(연출, 극본, 음악 등)는 반드시 이름 뒤에 괄호로 역할을 적어줘. (예: 봉준호(연출), 정재일(음악), 김은숙(극본))
       - 주연 배우는 괄호 없이 이름만 적어줘. (예: 송강호, 김고은)
       - 중요도 순으로 섞어서 3~4명 정도 콤마(,)로 구분.
    
    JSON 예시:
    {{
        "platform": "Netflix",
        "rating": 4.5,
        "release_date": "2025-01-01",
        "running_time": 130,
        "cast_crew": "이응복(연출), 김고은, 공유, 김은숙(극본)"
    }}
    """
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        st.error(f"AI 분석 실패: {e}")
        return
