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

# --- 3. AI 분석 (안정적인 gemini-pro 사용) ---
def analyze_content(title, combined_comment):
    genai.configure(api_key=st.secrets["gemini_api_key"])
    
    # 404 에러 방지를 위한 표준 모델 사용
    model = genai.GenerativeModel("gemini-pro")
    
    prompt = f"""
    작품명: '{title}'
    누적 코멘트: '{combined_comment}'
    
    위 정보를 바탕으로 JSON 형식으로만 답해줘.
    
    1. platform: Netflix, Disney+, Prime Video, Apple TV+, Watcha, TVING, Wavve, Cinema 중 1개.
    2. rating: 전체 뉘앙스 분석하여 1.0~5.0 사이 점수 (0.5 단위).
    3. release_date: 최초 공개일 (YYYY-MM-DD).
    4. running
