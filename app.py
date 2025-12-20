import streamlit as st
import pandas as pd
from streamlit_searchbox import st_searchbox
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import requests
from collections import Counter

# --- 페이지 설정 ---
st.set_page_config(page_title="My Media Archive", page_icon="🎬", layout="wide")

# --- 0. URL Selection Handler (Clickable Cards) ---
# Grid에서 카드를 클릭했을 때 URL 파라미터를 통해 선택을 감지하고 처리합니다.
if "sel_id" in st.query_params:
    try:
        mid = st.query_params["sel_id"]
        mtype = st.query_params.get("sel_type", "movie")
        st.session_state['url_selection_pending'] = {"id": mid, "type": mtype}
        st.query_params.clear()
    except:
        pass

import streamlit as st
try:
    from st_keyup import st_keyup
except ImportError:
    try:
        from streamlit_keyup import st_keyup
    except ImportError:
        st_keyup = None
        st.warning("Install streamlit-keyup for live search functionality: pip install streamlit-keyup")
    
# --- Custom CSS (Threads Aesthetic) ---
st.markdown("""
<style>
    /* Movie Card CSS for Clickable Grid */
    .movie-card-link {
        text-decoration: none !important;
        color: inherit !important;
        display: block;
    }
    .movie-card {
        border-radius: 12px;
        overflow: hidden;
        transition: transform 0.2s, box-shadow 0.2s;
        border: 1px solid rgba(255,255,255,0.1);
        background: #1E1E1E;
        color: white;
        display: block;
        height: 100%; /* Make items uniform height */
        position: relative;
    }
    .movie-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 24px rgba(0,0,0,0.6);
        border-color: rgba(255,255,255,0.4);
        z-index: 10;
        cursor: pointer;
    }
    .movie-card img {
        width: 100%;
        display: block;
        aspect-ratio: 2/3;
        object-fit: cover;
    }
    .movie-card .card-info {
        padding: 10px;
        text-align: center;
        background: linear-gradient(to bottom, #1E1E1E, #101010);
    }
    .movie-card .card-title {
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: #fff;
    }
    .movie-card .card-year {
        font-size: 0.75rem;
        color: #bbb;
    }
    /* Link Reset */
    a:hover { text-decoration: none; }

    /* 1. Global Background & Font */
    .stApp {
        background-color: #101010;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* 2. Optimize Layout (Full Width & No Header Gap) */
    header[data-testid="stHeader"] {
        display: none !important; /* Completely hide extra top bar */
    }
    .block-container {
        padding-top: 0rem !important; /* Move content up to the VERY top */
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 98% !important; /* Standard width */
    }

    /* 3. Text Color (High Contrast) */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {
        color: #F3F5F7 !important;
    }
    
    /* 4. Buttons (Pill Shape, White) */
    .stButton > button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-radius: 24px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #E0E0E0 !important;
        transform: scale(1.02);
    }
    
    /* Primary Action Buttons (if different) */
    
    /* 5. Inputs (Minimalist Gray) */
    .stTextInput > div > div > input {
        background-color: #1E1E1E !important;
        color: #F3F5F7 !important;
        border: 1px solid #333333;
        border-radius: 12px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #888888;
        color: #FFFFFF !important;
    }
    
    /* Date Input */
    .stDateInput > div > div > input {
        background-color: #1E1E1E !important;
        color: #F3F5F7 !important;
        border: 1px solid #333333;
        border-radius: 12px;
    }

    /* Selectbox & Radio Styles */
    .stSelectbox > div > div {
        background-color: #1E1E1E !important;
        color: #F3F5F7 !important;
        border: 1px solid #333333;
        border-radius: 12px;
    }
    .stRadio label {
        color: #F3F5F7 !important;
    }
    
    /* Expander/Container Borders */
    .streamlit-expanderHeader {
        background-color: #101010 !important;
        color: #F3F5F7 !important;
    }

    /* 6. Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px;
        color: #777777;
        font-size: 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: transparent;
        color: #FFFFFF !important;
        font-weight: bold;
        border-bottom: 2px solid #FFFFFF;
    }

    /* 7. Containers/Cards */
    [data-testid="stForm"] {
        background-color: #181818;
        border: 1px solid #333;
        border-radius: 16px;
        padding: 20px;
    }
    .stContainer {
        border-radius: 16px;
    }
    
    /* Toast override */
    div[data-baseweb="toast"] {
        background-color: #333 !important;
        color: white;
        border-radius: 12px;
    }
    /* 8. Suggestion Buttons (Ultra-Compact, Left-Aligned) */
    /* 8. Suggestion Buttons (Strict Left Align & Ultra Compact) */
    div.stButton {
        margin-bottom: 0px !important; /* Wrapper 0 margin */
    }
    div.stButton > button[kind="secondary"] {
        background-color: transparent !important;
        border: none !important;
        color: #CCCCCC !important;
        text-align: left !important;
        display: flex !important;
        justify-content: flex-start !important;
        padding: 4px 12px !important; /* Visual padding for text */
        margin: 0px !important;
        height: auto !important;
        min-height: 28px !important; /* Ultra compact height */
        width: 100% !important;
        border-radius: 0px !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        background-color: #333333 !important;
        color: white !important;
    }
    div.stButton > button[kind="secondary"] > div {
        justify-content: flex-start !important;
    }
    div.stButton > button[kind="secondary"] p {
        font-size: 15px !important;
        margin: 0px !important;
        padding: 0px !important;
        line-height: 1.2 !important;
        text-align: left !important;
    }

    /* 9. Layout Tightening (Ultra Compact Mode) */
    [data-testid="column"] [data-testid="stVerticalBlock"] {
        gap: 0rem !important;
    }
    [data-testid="stElementContainer"] {
        margin-bottom: 0px !important;
    }
    iframe[title="st_keyup.st_keyup"] {
        height: 42px !important; /* Force compacted height */
        margin-bottom: 0px !important;
        display: block !important;
    }

    /* Suggestion Box Specifics */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-top-left-radius: 0px !important;
        border-top-right-radius: 0px !important;
        border-top: none !important; /* Visually merge with input */
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div:first-child {
        padding: 0px 0px !important; /* Remove Default Container Padding */
    }
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {
        gap: 0px !important; /* No gap between recommendation items */
    }
    
    /* Primary Button (Save/Analyze) remains distinct */
    button[kind="primary"] {
        border-radius: 20px !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

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
# --- 1. 구글 시트 연결 ---
@st.cache_resource
def get_sheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("media_db").sheet1

# --- 1-1. 데이터 읽기 최적화 (캐싱) ---
# 60초마다 캐시 만료 (잦은 API 호출 방지)
@st.cache_data(ttl=60)
def get_cached_records():
    sheet = get_sheet_connection()
    return sheet.get_all_records()

# 캐시 강제 초기화 함수 (데이터 수정 시 호출)
def clear_sheet_cache():
    get_cached_records.clear()

# --- 2. TMDB 상세 정보 검색 (US Provider 포함) ---
@st.cache_data(ttl=3600)
def search_candidates(query):
    """검색어에 대한 후보군 리스트 반환 (Disambiguation용)"""
    try:
        api_key = st.secrets.get("tmdb_api_key")
        if not api_key: return []
        
        # 1. 기본 검색
        search_url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={query}&language=ko-KR&page=1"
        response = requests.get(search_url)
        results = response.json().get('results', [])
        
        # 2. 결과 없으면 Smart Search 시도
        if not results:
            refined_query = refine_search_query(query)
            if refined_query and refined_query != query:
                # st.toast는 캐시되는 함수 내에서 호출 시 한 번만 실행되므로 주의, 하지만 유용함.
                # live search에서는 너무 빈번할 수 있으니 제외하거나 유지? 
                # -> 유지하되 live search 호출 시에는 toast가 안 뜰 수 있음 (캐시 hit). 괜찮음.
                search_url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={refined_query}&language=ko-KR&page=1"
                response = requests.get(search_url)
                results = response.json().get('results', [])
        
        # 필요한 정보만 정제해서 반환
        candidates = []
        for item in results:
            if item.get('media_type') not in ['movie', 'tv']: continue
            
            date = item.get('release_date') or item.get('first_air_date') or ""
            candidates.append({
                "id": item.get('id'),
                "media_type": item.get('media_type'),
                "title": item.get('title') or item.get('name'),
                "date": date,
                "poster_path": item.get('poster_path')
            })
        return candidates
    except:
        return []

def get_tmdb_detail(media_type, media_id):
    """ID로 상세 정보 조회 (기존 get_tmdb_data의 후반부)"""
    try:
        api_key = st.secrets.get("tmdb_api_key")
        
        # 1. 상세 정보 조회 (한글)
        details_url = f"https://api.themoviedb.org/3/{media_type}/{media_id}?api_key={api_key}&language=ko-KR&append_to_response=watch/providers,credits"
        details = requests.get(details_url).json()
        
        # --- Overview Fallback (English if Metadata missing) ---
        overview = details.get('overview', '')
        if not overview:
            try:
                en_url = f"https://api.themoviedb.org/3/{media_type}/{media_id}?api_key={api_key}&language=en-US"
                res_en = requests.get(en_url).json()
                if res_en.get('overview'):
                    overview = f"(영어 원문) {res_en['overview']}"
            except:
                pass

        # --- 데이터 추출 (기존 로직 재사용) ---
        poster_path = details.get('poster_path')
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
        
        # Provider Priority: KR -> US
        providers = details.get('watch', {}).get('providers', {}).get('results', {}).get('KR', {})
        if not providers: 
            providers = details.get('watch', {}).get('providers', {}).get('results', {}).get('US', {})
        
        flatrate = providers.get('flatrate', [])
        platform_list = [p['provider_name'] for p in flatrate]
        
        # [Fallback Logic] If no streaming provider found
        if not platform_list:
            if media_type == 'tv':
                # For TV, check broadcast networks (e.g. tvN, Disney+, Netflix)
                networks = details.get('networks', [])
                if networks:
                     platform_list = [n['name'] for n in networks]
            elif media_type == 'movie':
                # For Movies, check Production Companies for OTT Originals (Netflix, etc.)
                # If matches known OTT, use it. Else default to Cinema.
                prod_companies = [c['name'] for c in details.get('production_companies', [])]
                ott_keywords = ["Netflix", "Disney", "Apple", "Amazon", "Watcha", "Coupang", "Wavve"]
                
                detected_ott = []
                for pc in prod_companies:
                    for kw in ott_keywords:
                        if kw.lower() in pc.lower():
                            detected_ott.append(kw)
                
                if detected_ott:
                    platform_list = list(set(detected_ott)) # Unique
                else:
                    platform_list = ["Cinema"]

        platform_str = ", ".join(platform_list[:3]) if platform_list else "Cinema/Other"
        
        if media_type == 'movie':
            release_date = details.get('release_date', '')
            runtime = details.get('runtime', 0)
        else:
            release_date = details.get('first_air_date', '')
            runtimes = details.get('episode_run_time', [])
            avg_runtime = runtimes[0] if runtimes else 30
            num_episodes = details.get('number_of_episodes', 1)
            runtime = avg_runtime * num_episodes
            platform_str += f" | {num_episodes}부작"
            
        cast = details.get('credits', {}).get('cast', [])
        crew = details.get('credits', {}).get('crew', [])
        
        directors = []
        cinematographers = []
        musicians = []
        
        if media_type == 'movie':
            directors = [m['name'] for m in crew if m['job'] == 'Director']
            cinematographers = [m['name'] for m in crew if m['job'] in ['Director of Photography', 'Cinematography']]
            musicians = [m['name'] for m in crew if m['job'] in ['Original Music Composer', 'Music']]
        else:
            directors = [m['name'] for m in details.get('created_by', [])]
            # TV shows might have crew in credits/crew, but 'created_by' is main for creators. 
            # We can still check crew for music/camera if available.
            if not directors:
                 directors = [m['name'] for m in crew if m['job'] == 'Director'] # Fallback
            
            cinematographers = [m['name'] for m in crew if m['job'] in ['Director of Photography', 'Cinematography']]
            musicians = [m['name'] for m in crew if m['job'] in ['Original Music Composer', 'Music']]
            
            
        actors = [m['name'] for m in cast[:5]] # Expand to 5
        
        director_str = f"{directors[0]}(연출)" if directors else ""
        cam_str = f"{cinematographers[0]}(촬영)" if cinematographers else ""
        music_str = f"{musicians[0]}(음악)" if musicians else ""
        actor_str = ", ".join(actors)
        
        # Combine all parts (Order: Director -> Actors -> Camera -> Music)
        credit_parts = [director_str, actor_str, cam_str, music_str]
        cast_crew_str = ", ".join([p for p in credit_parts if p]).strip(', ')
        
        return {
            "title": details.get('title') or details.get('name'),
            "poster_url": poster_url,
            "poster_path": poster_path, # [Added] Compatibility for Rec UI
            "platform": platform_str,
            "release_date": release_date,
            "running_time": runtime,
            "cast_crew": cast_crew_str,
            "tmdb_id": media_id,
            "media_type": media_type,
            "genre_ids": details.get('genre_ids', []),
            
            # [Added] Rich Details for UI
            "overview": overview,
            "genres": [g['name'] for g in details.get('genres', [])],
            "directors": directors,
            "cinematographers": cinematographers,
            "musicians": musicians,
            "cast": actors,
            "vote_average": details.get('vote_average', 0.0),
            
            # [Compatibility] Keys for search/selection interface
            "id": media_id,
            "date": release_date
        }
    except Exception as e:
        print(f"Detail Fetch Error: {e}")
        return None

# --- 2. TMDB 상세 정보 검색 (US Provider 포함) ---
def get_tmdb_data(query):
    cands = search_candidates(query)
    if not cands: return None
    return get_tmdb_detail(cands[0]['media_type'], cands[0]['id'])

def _tmdb_data_legacy(query):
    try:
        api_key = st.secrets.get("tmdb_api_key")
        if not api_key: return None
        
        # 1. 검색 (한글로 검색)
        search_url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={query}&language=ko-KR&page=1"
        response = requests.get(search_url)
        results = response.json().get('results', [])
        
        if not results:
            # 1차 검색 실패 -> Smart Search (LLM 보정) 시도
            print(f"1차 검색 실패: {query}. Smart Search 시도...")
            refined_query = refine_search_query(query)
            if refined_query and refined_query != query:
                st.toast(f"💡 '{query}' 대신 '{refined_query}' 찾기 시도...")
                search_url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={refined_query}&language=ko-KR&page=1"
                response = requests.get(search_url)
                results = response.json().get('results', [])
        
        if not results: return None
        
        # 가장 정확한 결과 선택 (보통 첫번째)
        target = results[0]
        media_type = target.get('media_type')
        if media_type not in ['movie', 'tv']: return None
        media_id = target['id']
        
        # 2. 상세 정보 조회 (Providers, Credits 포함)
        details_url = f"https://api.themoviedb.org/3/{media_type}/{media_id}?api_key={api_key}&language=ko-KR&append_to_response=watch/providers,credits"
        details = requests.get(details_url).json()
        
        # --- 데이터 추출 ---
        # 1. 포스터
        poster_path = details.get('poster_path')
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
        
        # 2. OTT 정보 (US 기준) & 부작 정보
        providers = details.get('watch', {}).get('providers', {}).get('results', {}).get('US', {})
        flatrate = providers.get('flatrate', [])
        platform_list = [p['provider_name'] for p in flatrate]
        platform_str = ", ".join(platform_list[:2]) if platform_list else "Cinema/Other" # 상위 2개만
        
        # 3. 개봉일 / 러닝타임 / 에피소드 수
        if media_type == 'movie':
            release_date = details.get('release_date', '')
            runtime = details.get('runtime', 0)
        else: # tv
            release_date = details.get('first_air_date', '')
            # TV는 episode_run_time이 리스트임 + 총 에피소드 수
            runtimes = details.get('episode_run_time', [])
            avg_runtime = runtimes[0] if runtimes else 30 # 기본값 30분
            num_episodes = details.get('number_of_episodes', 1)
            
            # 총 시청 시간 계산 (평균 러닝타임 x 에피소드 수)
            runtime = avg_runtime * num_episodes
            
            # 드라마는 몇 부작인지 플랫폼 정보에 괄호로 병기 (DB 스키마 유지 위함)
            # 예: Netflix | 16부작
            platform_str += f" | {num_episodes}부작"
            
        # 4. 제작진 (감독/주연)
        cast = details.get('credits', {}).get('cast', [])
        crew = details.get('credits', {}).get('crew', [])
        
        # 감독 (Directing or Creator for TV)
        directors = []
        if media_type == 'movie':
            directors = [m['name'] for m in crew if m['job'] == 'Director']
        else:
            directors = [m['name'] for m in details.get('created_by', [])]
            
        actors = [m['name'] for m in cast[:3]]
        
        director_str = f"{directors[0]}(연출)" if directors else ""
        actor_str = ", ".join(actors)
        cast_crew_str = f"{director_str}, {actor_str}".strip(', ')
        
        return {
            "title": details.get('title') or details.get('name'), # 정확한 공식 제목
            "poster_url": poster_url,
            "platform": platform_str,
            "release_date": release_date,
            "running_time": runtime,
            "cast_crew": cast_crew_str,
            "cast_crew": cast_crew_str,
            "tmdb_id": media_id,
            "media_type": media_type,
            "genre_ids": details.get('genre_ids', []) # 장르 정보 추가
        }

    except Exception as e:
        print(f"TMDB Error: {e}")
        return None

def find_proxy_seed(current_platform, current_rating, history_df, target_media_type='movie'):
    """
    현재 작품 대신 추천의 씨앗이 될 '과거의 명작'을 찾습니다.
    전략: 미디어 타입(Movie/TV) 일치 -> 플랫폼 일치 -> 평점 일치
    """
    try:
        if history_df.empty: return None
        
        # 1. 미디어 타입 필터링 (Inference)
        # 시트에 Type 컬럼이 없으므로 추론: '부작' 텍스트가 있거나 러닝타임이 200분 넘으면 TV로 간주
        def infer_type(row):
            p = str(row.get('Platform', ''))
            rt = float(row.get('RunningTime', 0)) if row.get('RunningTime') else 0
            if "부작" in p or rt > 200: return 'tv'
            return 'movie'
            
        history_df['InferredType'] = history_df.apply(infer_type, axis=1)
        
        # 타겟 타입과 일치하는 후보군 우선 필터링
        type_candidates = history_df[history_df['InferredType'] == target_media_type]
        
        # 만약 타입 매칭되는게 하나도 없으면? (예: 드라마 처음 등록 시) -> 어쩔 수 없이 전체 사용
        if type_candidates.empty:
            type_candidates = history_df
            
        # 2. 플랫폼 매칭 (느슨한 장르/분위기 매칭 효과)
        # 플랫폼 이름이 정확히 일치하지 않을 수 있으므로 포함 여부 확인
        
        # 단순화를 위해 플랫폼 텍스트가 포함된 것들 필터링
        if not current_platform or current_platform == "Unknown":
            platform_candidates = type_candidates
        else:
            base_platform = current_platform.split('|')[0].strip() # "Netflix | 8부작" -> "Netflix"
            platform_candidates = type_candidates[type_candidates['Platform'].str.contains(base_platform, na=False, case=False)]
            
            # 만약 같은 플랫폼 기록이 없으면 전체 타입 후보군에서 찾음
            if platform_candidates.empty:
                platform_candidates = type_candidates
        
        # 2. 평점 필터링
        candidates = pd.DataFrame()
        if current_rating >= 3.0:
            # 만족 (High): 나와 코드가 비슷한(평점이 비슷한) 작품 찾기
            # 예: 4.0점 줬으면 3.5점 이상인 것들
            candidates = platform_candidates[platform_candidates['Rating'] >= (current_rating - 0.5)]
        else:
            # 불만족 (Low): 눈 정화용 명작 (3.0 이상 무조건)
            candidates = platform_candidates[platform_candidates['Rating'] >= 3.0]
            
        if candidates.empty: return None
        
        # 3. 최신 기록 우선 (Index 역순)
        # 가장 최근에 본 '비슷한 수준'의 작품을 반환
        seed_row = candidates.iloc[-1] 
        
        # 시트에는 TMDB ID가 없으므로... 제목으로 다시 검색해야 함 (비효율적이지만 현재 구조상 최선)
        return seed_row['Title']
    except:
        return None

def get_recommendation(tmdb_data, user_rating, existing_titles=[]):
    try:
        api_key = st.secrets.get("tmdb_api_key")
        if not api_key: return None
        
        media_type = tmdb_data.get('media_type', 'movie')
        rec_source_id = tmdb_data.get('tmdb_id')
        rec_mode = "Direct"

        # --- 1. Proxy Seed Logic (과거 기록 기반 씨앗 찾기) ---
        # 시트 데이터 가져오기
        try:
             # 캐시된 데이터 사용
             records = get_cached_records()
             df_history = pd.DataFrame(records)
             if not df_history.empty:
                 df_history['Rating'] = pd.to_numeric(df_history['Rating'], errors='coerce')
                 
                 # [Modified] Pass media_type to prioritize same-type recommendations
                 proxy_title = find_proxy_seed(tmdb_data.get('platform'), user_rating, df_history, media_type)
                 
                 if proxy_title and proxy_title != tmdb_data.get('title'):
                     # Proxy Seed를 찾았으면, 얘의 ID를 구해야 함
                     # (주의: API 호출 추가됨)
                     proxy_tmdb = get_tmdb_data(proxy_title)
                     if proxy_tmdb:
                         rec_source_id = proxy_tmdb.get('tmdb_id')
                         media_type = proxy_tmdb.get('media_type', 'movie') # Proxy의 타입 따라감
                         rec_mode = f"Proxy({proxy_title})"
        except:
             pass # Proxy 실패하면 그냥 원래 ID 사용

        # --- 2. 추천 API 호출 ---
        # 전략 구분없이 일단 'Recommendations' 엔드포인트가 가장 퀄리티가 좋음 (장르/분위기/캐스팅 통합)
        # Low Rating일 때 Discover를 쓰는 것보다, '검증된 명작(Proxy)'의 Recommendation을 쓰는게 더 정확함.
        
        url = f"https://api.themoviedb.org/3/{media_type}/{rec_source_id}/recommendations?api_key={api_key}&language=ko-KR&page=1"
        response = requests.get(url)
        results = response.json().get('results', [])
        
        if results:
            # --- 3. 정렬 (최신순) ---
            def get_date(x):
                d = x.get('release_date') or x.get('first_air_date')
                return d if d else "0000-00-00"
            
            results.sort(key=get_date, reverse=True)

            # --- 4. 필터링 (안 본 것) ---
            for rec in results:
                title = rec.get('title') or rec.get('name')
                if title not in existing_titles:
                    # [Updated] Fetch Full Details (Director, Cast) for the best recommendation
                    detail = get_tmdb_detail(rec.get('media_type', 'movie'), rec.get('id'))
                    if detail:
                        detail['rec_mode'] = rec_mode
                        return detail
                    # Fallback if detail fetch fails
                    return {
                        "title": title,
                        "id": rec.get('id'),
                        "media_type": rec.get('media_type', 'movie'),
                        "poster_path": rec.get('poster_path'),
                        "overview": rec.get('overview'),
                        "rec_mode": rec_mode
                    }
        
        # --- Fallback: 추천 결과가 아예 없으면 Trending에서 가져옴 ---
        # "이 영화랑 비슷한 건 없지만, 요즘 뜨는 건 이거야"
        if not results:
            try:
                url_trend = f"https://api.themoviedb.org/3/trending/movie/week?api_key={api_key}&language=ko-KR"
                res_trend = requests.get(url_trend).json().get('results', [])
                for rec in res_trend:
                    title = rec.get('title') or rec.get('name')
                    if title not in existing_titles:
                        # [Updated] Fetch Full Details for Fallback too
                        detail = get_tmdb_detail(rec.get('media_type', 'movie'), rec.get('id'))
                        if detail:
                            detail['rec_mode'] = f"Trending(Fallback)"
                            return detail
                        
                        return {
                            "title": title,
                            "id": rec.get('id'),
                            "media_type": rec.get('media_type', 'movie'),
                            "poster_path": rec.get('poster_path'),
                            "overview": rec.get('overview'),
                            "rec_mode": f"Trending(Fallback)"
                        }
            except:
                pass

        return None
    except:
        return None

# Groq 클라이언트 & Gemini 설정
import groq
import google.generativeai as genai

# Gemini 설정
try:
    if "gemini_api_key" in st.secrets:
        genai.configure(api_key=st.secrets["gemini_api_key"])
except:
    pass
@st.cache_data(show_spinner=False)
def refine_search_query(raw_query):
    # LLM을 사용하여 엉망인 검색어를 공식 제목으로 보정
    try:
        if not raw_query: return None
        
        prompt = f"사용자가 영화나 드라마 제목을 입력했는데, 오타가 있거나 줄임말일 수 있어: '{raw_query}'\n"
        prompt += "이것의 정확한 한국어 공식 제목(Official Title)이 뭘까? JSON으로 답해줘.\n"
        prompt += 'JSON 예시: {"official_title": "오징어 게임"}'
        
        client = groq.Groq(api_key=st.secrets["groq_api_key"])
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
        )
        return json.loads(chat_completion.choices[0].message.content).get('official_title')
    except:
        return None

def get_recent_examples():
    # 시트에서 최근 5개 리뷰(코멘트+평점) 가져와서 학습 데이터(Few-Shot)로 사용
    try:
        # 캐시된 데이터 사용
        records = get_cached_records()
        df = pd.DataFrame(records)
        if df.empty: return []
        
        # 날짜순 정렬 (최신이 뒤에 있다고 가정 or Date 컬럼 활용)
        # df는 보통 append 되므로 뒤쪽이 최신
        examples = []
        for i in range(len(df)-1, -1, -1):
            if len(examples) >= 5: break
            row = df.iloc[i]
            comment = row.get('Comment', '')
            rating = row.get('Rating', '')
            title = row.get('Title', '')
            platform = row.get('Platform', '')
            cast_crew = row.get('CastCrew', '') or row.get('Cast/Crew', '') # Fallback for header name
            
            if comment and rating:
                examples.append(f"Title: {title} | Review: '{comment}' -> Rating: {rating} | Info: {platform}, {cast_crew}")
        return "\n".join(examples)
    except:
        return ""
@st.cache_data(show_spinner=False)
def analyze_rating_only(comment, examples=""):
    # AI 평점 분석 (Few-Shot Context 포함)
    prompt = "너는 영화/드라마 평론가야. 리뷰를 보고 1.0~5.0 사이의 평점을 매겨 (0.5 단위).\n"
    
    if examples:
        prompt += f"참고: 이 사용자는 과거에 이렇게 평가했어 (이 톤을 학습해서 비슷하게 매겨줘):\n{examples}\n\n"
        
    prompt += f"새로운 리뷰: '{comment}'\n"
    prompt += "JSON 포맷으로 출력해. 예시: {\"rating\": 3.5}"

    # 1차 시도: Groq
    try:
        client = groq.Groq(api_key=st.secrets["groq_api_key"])
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
        )
        return json.loads(chat_completion.choices[0].message.content).get('rating', 0.0)
    except Exception as e_groq:
        # 2차 시도: Gemini
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            return json.loads(response.text).get('rating', 0.0)
        except:
            return 0.0 # 실패 시 기본값

@st.cache_data(ttl=600, show_spinner=False)
def generate_user_nickname():
    """유저의 취향을 분석하여 별명, 아이콘, 인사말, 히어로 이미지 생성"""
    # 0. Default State (Static Fallback)
    default_data = {
        "nickname": "씨네필", 
        "greeting": "기록은 기억을 지배합니다.", 
        "icon": "🎬", 
        "hero_image": ""
    }
    
    api_key = st.secrets.get("tmdb_api_key")
    
    try:
        # 1. 고득점 기록 조회
        records = get_cached_records()
        df = pd.DataFrame(records)
        
        # --- [CASE A] Empty DB: Show Trending Movie Backdrop ---
        if df.empty:
            if api_key:
                try:
                    url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={api_key}&language=ko-KR"
                    data = requests.get(url).json()
                    if data.get('results'):
                        top_trend = data['results'][0]
                        backdrop = top_trend.get('backdrop_path')
                        if backdrop:
                            default_data['hero_image'] = f"https://image.tmdb.org/t/p/original{backdrop}"
                        default_data['nickname'] = "새로운 탐험가"
                        default_data['greeting'] = f"오늘 '{top_trend.get('title')}' 어때요?"
                        default_data['icon'] = "✨"
                except:
                    pass
            return default_data

        # --- [CASE B] Specific User Persona ---
        
        # Rating 변환
        df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
        
        # Hero Image Selection (Highest Rated -> Get Backdrop)
        hero_image = ""
        try:
            top_works = df.sort_values(by=['Rating', 'Date'], ascending=[False, False])
            # Find first with valid title to search
            for _, row in top_works.iterrows():
                title = row['Title']
                # Search TMDB for Backdrop (High Quality)
                if api_key:
                    search_url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={title}&language=ko-KR"
                    res = requests.get(search_url).json()
                    if res.get('results'):
                        cand = res['results'][0]
                        bd_path = cand.get('backdrop_path')
                        if bd_path:
                            hero_image = f"https://image.tmdb.org/t/p/original{bd_path}"
                            break
                        elif cand.get('poster_path'): # Fallback to HD Poster
                             hero_image = f"https://image.tmdb.org/t/p/original{cand.get('poster_path')}"
                             break
                
                # If API fail, use stored Image (Poster)
                img_url = str(row.get('Image', ''))
                if img_url.startswith('http'):
                    hero_image = img_url
                    break
        except Exception as e:
            print(f"Hero Image Error: {e}")
            
        # 4.0 이상인 작품들만 필터링 (최신순 10개)
        high_rated = df[df['Rating'] >= 4.0].tail(10)
        
        favorites = []
        if not high_rated.empty:
            favorites = high_rated['Title'].tolist()
        else:
            favorites = df.tail(5)['Title'].tolist()
            
        favorites_str = ", ".join(favorites)
        
        # 2. LLM Prompt
        prompt = f"""
        사용자의 최근 선호 영화목록: [{favorites_str}]
        
        이 취향에 맞춰 다음 3가지를 JSON으로 생성해:
        1. "nickname": 이 취향을 가진 사람의 멋진 한국어 별명 (예: "밤의 추적자", "로맨스 장인").
        2. "icon": 그 별명에 딱 어울리는 이모지(Emoji) 1개.
        3. "greeting": 그 별명에 어울리는, 영화 명대사를 패러디한 짧고 재치 있는 환영 인사 (한국어). 
           (닉네임 포함 금지. 명대사 느낌나게).
           
        예시:
        {{
            "nickname": "밤의 추적자",
            "icon": "🦇",
            "greeting": "나는 복수다... 아니, 나는 당신의 기록이다."
        }}
        """
        
        # 1차: Groq (Llama 3)
        client = groq.Groq(api_key=st.secrets["groq_api_key"])
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=1.0 
        )
        result = json.loads(chat_completion.choices[0].message.content)
        
        # Merge Hero Image
        result['hero_image'] = hero_image
        return result
            
    except Exception as e:
        print(f"Nickname Gen Error: {e}")
        return default_data

# --- [Logic] URL Selection Processing ---
if st.session_state.get('url_selection_pending'):
    pending_sel = st.session_state.pop('url_selection_pending')
    # Fetch Detail
    try:
        # get_tmdb_detail must be defined by now
        full_detail = get_tmdb_detail(pending_sel['type'], pending_sel['id'])
        if full_detail:
            st.session_state['temp_selection'] = full_detail
            st.session_state['confirm_step'] = False
            st.session_state['recommendation_candidate'] = None
    except Exception as e:
        print(f"URL Selection Error: {e}")

# --- 4. 화면 구성 ---
user_data = generate_user_nickname()

# Safely extract data
if isinstance(user_data, dict):
    nickname = user_data.get('nickname', '씨네필')
    greeting = user_data.get('greeting', '어서오세요.')
    icon = user_data.get('icon', '🎬')
    hero_bg = user_data.get('hero_image', '')
else:
    nickname = "씨네필"
    greeting = "기록이 기억을 지배합니다."
    icon = "📽️"
    hero_bg = ""

# Fallback BG if plain
bg_style = f"background-image: linear-gradient(to bottom, rgba(0,0,0,0.3), rgba(0,0,0,0.9)), url('{hero_bg}');" if hero_bg else "background: linear-gradient(135deg, #1e1e1e 0%, #000000 100%);"

# Hero Header HTML (Click to Reset)
st.markdown(f"""
<a href="/" target="_self" style="text-decoration: none; display: block; margin-bottom: 25px;">
    <div style="
        position: relative;
        width: 100vw;
        left: 50%;
        margin-left: -50vw;
        height: 240px;
        border-radius: 0px;
        {bg_style}
        background-size: cover;
        background-position: center 20%;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        padding: 35px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        border: 1px solid rgba(255,255,255,0.1);
    ">
        <div style="
            color: rgba(255,255,255,0.9);
            font-size: 1.1rem;
            margin-bottom: 4px;
            font-weight: 600;
            text-shadow: 0 2px 4px rgba(0,0,0,0.8);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        ">"{greeting}"</div>
        <div style="
            color: #fff;
            font-size: 3.2rem;
            font-weight: 900;
            text-shadow: 0 4px 12px rgba(0,0,0,0.8);
            line-height: 1.1;
            letter-spacing: -1.5px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        ">{icon} {nickname}</div>
    </div>
</a>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📝 기록하기", "📌 찜 목록", "📊 인사이트/통계"])

# [탭 1] 입력 및 업데이트
with tab1:
    # --- Session State 초기화 ---
    if 'confirm_step' not in st.session_state:
        st.session_state['confirm_step'] = False
        st.session_state['pending_data'] = None
        st.session_state['duplicate_info'] = None
        st.session_state['recommendation_candidate'] = None # 추천 상태 추가

    # --- 입력 폼 (이전 단계가 아닐 때만 보임) ---
    # --- 입력 모드 분기 (Confirm vs Rec vs Normal) ---
    # [모드 2] 추천 꼬리물기 (Rec Mode)
    if st.session_state.get('recommendation_candidate') and not st.session_state['confirm_step']:
        # [모드 2] 추천 꼬리물기 (Rec Mode)
        rec = st.session_state['recommendation_candidate']
        with st.container(border=True):
            st.markdown("### 🍿 꼬리에 꼬리를 무는 기록")
            st.write(f"방금 본 작품과 비슷한 **'{rec['title']}'**, 혹시 보셨나요?")
            
            c1, c2 = st.columns([1, 4])
            with c1:
                if rec['poster_path']:
                    st.image(f"https://image.tmdb.org/t/p/w200{rec['poster_path']}")
                else:
                    st.markdown("🎬")
            
            with c2:
                # [Added] Director & Cast Info
                if rec.get('directors'):
                     st.caption(f"🎬 감독: {', '.join(rec['directors'])}")
                if rec.get('cinematographers'):
                     st.caption(f"📷 촬영: {', '.join(rec['cinematographers'][:2])}")
                if rec.get('musicians'):
                     st.caption(f"🎵 음악: {', '.join(rec['musicians'][:2])}")
                if rec.get('cast'):
                     st.caption(f"🎭 출연: {', '.join(rec['cast'][:5])}")
                
                st.info(rec.get('overview', '줄거리 정보 없음')[:150] + "...")
                
                with st.form("quick_add_form"):
                    quick_comment = st.text_input("한줄평 남기기 (입력 시 평점 확인 단계로 이동)", placeholder="예: 이것도 명작이지")
                    quick_submit = st.form_submit_button(f"'{rec['title']}' 기록 시작 ⚡")
                    
                    if quick_submit and quick_comment:
                        # 퀵 저장 -> Confirm UI로 데이터 넘기기
                        with st.spinner("정보 불러오는 중..."):
                            tmdb_quick = get_tmdb_data(rec['title'])                         
                            if tmdb_quick:
                                # 임시 데이터 저장 (입력 폼과 동일한 구조)
                                st.session_state['pending_data'] = {
                                    'user_title': rec['title'],
                                    'comment': quick_comment,
                                    'date': None,
                                    'tmdb': tmdb_quick 
                                }
                                # 중복 체크
                                # 캐시 사용
                                records = get_cached_records()
                                all_titles = [r['Title'] for r in records]
                                
                                if tmdb_quick['title'] in all_titles:
                                    # 중복이면 dup_info를 채워서 보냄 (Merge 유도)
                                    df_existing = pd.DataFrame(records)
                                    idx = df_existing[df_existing['Title'] == tmdb_quick['title']].index[0]
                                    st.session_state['duplicate_info'] = {
                                        'index': idx,
                                        'row_idx': idx + 2,
                                        'old_comment': df_existing.iloc[idx]['Comment'],
                                        'old_rating': pd.to_numeric(df_existing.iloc[idx]['Rating'], errors='coerce'),
                                        'old_image': df_existing.iloc[idx]['Image']
                                    }
                                else:
                                    st.session_state['duplicate_info'] = None

                                st.session_state['confirm_step'] = True # Confirm UI로 이동
                                st.session_state['recommendation_candidate'] = None # 추천 카드 숨김
                                st.rerun()
                            else:
                                st.error("정보를 찾을 수 없습니다.")

        # --- [변경] 3-Way Action Buttons (찜 / 차단 / 패스) ---
        c_wish, c_ban, c_pass = st.columns(3)
        
        # 공통 함수: 다음 추천으로 넘어가기
        def next_rec_step(seed_tmdb, rating, skipped_list=[]):
            # 캐시 사용
            records = get_cached_records()
            all_titles = [r['Title'] for r in records] 
            # Pass한 것들도 제외 목록에 포함
            all_titles.extend(skipped_list)
            
            rec_item = get_recommendation(seed_tmdb, rating, existing_titles=all_titles)
            if rec_item:
                st.session_state['recommendation_candidate'] = rec_item
                st.toast("🚀 다음 추천작을 가져왔습니다!")
            else:
                st.session_state['recommendation_candidate'] = None
                st.toast("더 이상 추천할 작품이 없습니다. 🏁")
            st.rerun()

        with c_wish:
            if st.button("📌 나중에 볼래요 (찜)", use_container_width=True):
                # 찜 저장 로직 (Rating="", Comment="[찜]")
                with st.spinner("찜 목록에 저장 중..."):
                    tmdb_wish = get_tmdb_data(rec['title'])
                    if tmdb_wish:
                        row_data = [
                            datetime.now().strftime("%Y-%m-%d"),
                            tmdb_wish['title'],
                            tmdb_wish['platform'],
                            "",  # Rating Empty
                            "[찜]", # Marker
                            tmdb_wish['release_date'],
                            tmdb_wish['poster_url'],
                            tmdb_wish['running_time'],
                            tmdb_wish['cast_crew']
                        ]
                        sheet = get_sheet_connection()
                        sheet.append_row(row_data)
                        clear_sheet_cache() # 데이터 변경 즉시 캐시 초기화
                        st.toast(f"'{rec['title']}' 찜 완료! 📌")
                        
                        # [Continuous Chain] 찜했으면 관심 있다는 뜻 -> High Rating 전략 (5.0)
                        temp_tmdb = get_tmdb_data(rec['title']) # Seed용
                        skipped = st.session_state.get('temp_skipped', [])
                        next_rec_step(temp_tmdb, 5.0, skipped)

        with c_ban:
            if st.button("🚫 취향 아님 (차단)", use_container_width=True):
                 # 차단 로직 (Rating=0, Comment="[관심없음]")
                 with st.spinner("관심 없음으로 처리 중..."):
                    tmdb_ban = get_tmdb_data(rec['title'])
                    if tmdb_ban:
                        row_data = [
                            datetime.now().strftime("%Y-%m-%d"),
                            tmdb_ban['title'],
                            tmdb_ban['platform'],
                            0.0,
                            "[관심없음]",
                            tmdb_ban['release_date'],
                            tmdb_ban['poster_url'],
                            tmdb_ban['running_time'],
                            tmdb_ban['cast_crew']
                        ]
                        sheet = get_sheet_connection()
                        sheet.append_row(row_data)
                        clear_sheet_cache() # 데이터 변경 즉시 캐시 초기화
                        st.toast(f"'{rec['title']}' 추천 제외 🚫")
                        
                        # [Redemption Logic] 차단 시, 내 인생작(4.0+) 기반으로 분위기 환기
                        records = get_cached_records()
                        high_rated_titles = []
                        for r in records:
                            try:
                                if float(r['Rating']) >= 4.0:
                                    high_rated_titles.append(r['Title'])
                            except:
                                continue
                        
                        if high_rated_titles:
                            import random
                            pivot_title = random.choice(high_rated_titles)
                            temp_tmdb = get_tmdb_data(pivot_title)
                            next_rating = 5.0
                            st.toast(f"🔄 취향 저격! '{pivot_title}' 스타일로 찾아볼게요.")
                        else:
                            # Fallback: No favorites found, use current (negative signal)
                            temp_tmdb = get_tmdb_data(rec['title']) 
                            next_rating = 0.0
                            
                        skipped = st.session_state.get('temp_skipped', [])
                        next_rec_step(temp_tmdb, next_rating, skipped)

        with c_pass:
            if st.button("➡️ 이번만 패스", use_container_width=True):
                # 저장 안함, 대신 skipped 목록에 추가
                if 'temp_skipped' not in st.session_state:
                    st.session_state['temp_skipped'] = []
                st.session_state['temp_skipped'].append(rec['title'])
                
                # [Continuous Chain] 패스는 중립/싫음 -> Low Rating 전략 (0.0)으로 분위기 환기
                # Seed는 현재 Pass한 작품 기준
                temp_tmdb = get_tmdb_data(rec['title'])
                next_rec_step(temp_tmdb, 0.0, st.session_state['temp_skipped'])

    elif not st.session_state['confirm_step']:
        
        def render_media_card(item, mode="input"):
            """
            Standardized Media Card Component.
            Modes:
            - 'input': Large Hero Style (Poster + Details) for selection confirmation.
            - 'grid': Compact Card (Poster + Title) for search results.
            """
            with st.container(border=True):
                poster_url = f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get('poster_path') else "https://via.placeholder.com/500x750?text=No+Image"
                
                if mode == "input":
                    cols = st.columns([1, 4])
                    with cols[0]:
                        st.image(poster_url, use_container_width=True)
                    with cols[1]:
                        st.title(item['title'])
                        
                        # Meta Info (Year | Runtime | TMDB Rating)
                        # get_tmdb_detail returns 'release_date', need to handle both key naming conventions if confusing
                        # In input mode, item comes from tmdb variable which has 'release_date'
                        r_date = item.get('release_date') or item.get('date') or ''
                        date_str = str(r_date)[:4]
                        
                        runtime_str = f"{item.get('running_time', 0)} min"
                        rating = item.get('vote_average', 0.0)
                        st.caption(f"{date_str} • {runtime_str} • ⭐ {rating:.1f} (TMDB)")

                        # Genres
                        if item.get('genres'):
                            st.markdown(f"categories: **{' / '.join(item['genres'])}**")

                        st.divider()
                        
                        # Director & Cast
                        if item.get('directors'):
                            st.markdown(f"**🎬 감독**: {', '.join(item['directors'])}")
                        if item.get('cast'):
                            st.markdown(f"**🎭 출연**: {', '.join(item['cast'][:5])} ...")
                        
                        # Platform
                        if item.get('platform'):
                             st.markdown(f"**📺 플랫폼**: {item['platform']}")
                        
                        st.divider()
                        
                        # Overview
                        overview = item.get('overview', '')
                        if overview:
                            st.info(overview)
                        else:
                             st.caption("줄거리 정보가 존재하지 않습니다.")
                            
                elif mode == "grid":
                    st.image(poster_url, use_container_width=True)
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"{str(item.get('date',''))[:4]}")

        # [모드 3] 일반 입력 (Normal Mode) - Live Search Applied
        st.markdown("### 📝 작품 기록")
        
        if 'temp_selection' not in st.session_state:
            st.session_state['temp_selection'] = None
        if 'search_query_state' not in st.session_state:
            st.session_state['search_query_state'] = ""

        # 1. Selection State Check (Final Stage)
        if st.session_state['temp_selection']:
            sel = st.session_state['temp_selection']
            
            # Show Selected Candidate UI using Standard Card
            render_media_card(sel, mode="input")
            
            if st.button("🔄 다시 검색", key="btn_re_search"):
                st.session_state['temp_selection'] = None
                st.rerun()

            st.divider()
            
            # Comment & Date Input
            input_comment = st.text_area("코멘트 (이 내용을 바탕으로 AI가 평점을 분석합니다)", height=150, placeholder="예: 결말이 너무 충격적이다. 배우들의 연기가 미쳤다...", key="analysis_comment")
            
            # Default Date: Release Date if available, else Today
            default_date = datetime.now()
            if sel.get('date'):
                try:
                    default_date = datetime.strptime(str(sel['date']), "%Y-%m-%d")
                except:
                    pass
            
            input_date = st.date_input("본 날짜 (기본값: 개봉일)", value=default_date, key="analysis_date")
            st.caption("AI가 당신의 코멘트를 분석하여 평점(0.0~5.0)을 제안합니다.")
            
            if st.button("🤖 AI 평점 분석 및 저장 (Analyze & Save)", type="primary", use_container_width=True):
                 # ... (Use existing logic, simplified here for replacement context, assume logic exists or I must inject details?)
                 # Wait, I am replacing the SAVE LOGIC too if I replace this block.
                 # I MUST include the save logic.
                 if not input_comment:
                    st.warning("코멘트를 입력해주세요!")
                 else:
                    with st.spinner("TMDB 정보 조회 및 AI 분석 중..."):
                        tmdb = get_tmdb_detail(sel['media_type'], sel['id'])
                        st.session_state['pending_data'] = {
                            'user_title': sel['title'], 'comment': input_comment, 'date': input_date, 'tmdb': tmdb 
                        }
                        # Duplicate Check logic
                        records = get_cached_records()
                        all_titles = [r['Title'] for r in records]
                        if tmdb['title'] in all_titles:
                            df_existing = pd.DataFrame(records)
                            idx = df_existing[df_existing['Title'] == tmdb['title']].index[0]
                            st.session_state['duplicate_info'] = {
                                'index': idx, 'row_idx': idx + 2,
                                'old_comment': df_existing.iloc[idx]['Comment'],
                                'old_rating': pd.to_numeric(df_existing.iloc[idx]['Rating'], errors='coerce'),
                                'old_image': df_existing.iloc[idx]['Image']
                            }
                        else:
                            st.session_state['duplicate_info'] = None
                        st.session_state['confirm_step'] = True
                        st.session_state['temp_selection'] = None
                        st.rerun()

        else:
            # 2. Search Mode (Standard Autocomplete + Full Grid Option)
            c_input, c_toggle = st.columns([0.85, 0.15])
            
            with c_input:
                def search_wrapper(searchterm):
                    if not searchterm: return []
                    try:
                        cands = search_candidates(searchterm)
                        if not cands: return []
                        
                        formatted_options = []
                        
                        # [Fix] Add "Search All" Option at the TOP so 'Enter' triggers grid view
                        formatted_options.append((f"🔍 '{searchterm}' 검색 결과 전체 보기 (썸네일)", {'special': 'search_grid', 'query': searchterm}))
                        
                        for c in cands:
                            date_str = str(c['date'])[:4] if c.get('date') else "N/A"
                            label = f"{c['title']} ({date_str})"
                            formatted_options.append((label, c))
                        
                        return formatted_options
                    except Exception as e:
                        print(f"Search Error: {e}")
                        return []

                # Unified Autocomplete
                selected_cand = st_searchbox(
                    search_wrapper,
                    key="tmdb_search_main",
                    placeholder="작품명 검색 (키보드 ↓/↑ 이동, Enter 선택)",
                    clear_on_submit=False,
                )
            
            with c_toggle:
                st.markdown('<div style="height: 5px;"></div>', unsafe_allow_html=True)
                if st.button("➕", help="직접 입력", key="btn_manual_toggle", use_container_width=True):
                    st.session_state['manual_entry_mode'] = not st.session_state['manual_entry_mode']
                    st.rerun()

            # Handle Selection
            if selected_cand:
                # Check for Special Actions
                if isinstance(selected_cand, dict) and selected_cand.get('special') == 'search_grid':
                     st.divider()
                     st.subheader(f"🎬 '{selected_cand['query']}' 검색 결과")
                     
                     # Render Grid
                     grid_cands = search_candidates(selected_cand['query'])
                     if grid_cands:
                         # [Fix] Dense Grid (6 cols) for smaller items as requested
                         cols = st.columns(6)
                         for idx, cand in enumerate(grid_cands):
                             with cols[idx % 6]:
                                 # HTML Card Link
                                 poster = f"https://image.tmdb.org/t/p/w500{cand.get('poster_path')}" if cand.get('poster_path') else "https://via.placeholder.com/500x750?text=No+Image"
                                 title = cand['title'].replace('"', '&quot;')
                                 date = str(cand.get('date',''))[:4]
                                 mid = cand['id']
                                 mtype = cand['media_type']
                                 
                                 st.markdown(f"""
                                 <a href="/?sel_id={mid}&sel_type={mtype}" target="_self" class="movie-card-link">
                                     <div class="movie-card">
                                         <img src="{poster}" />
                                         <div class="card-info">
                                             <div class="card-title">{title}</div>
                                             <div class="card-year">{date}</div>
                                         </div>
                                     </div>
                                 </a>
                                 """, unsafe_allow_html=True)
                     else:
                         st.warning("결과가 없습니다.")
                else:
                    # Normal Item Selection
                    st.session_state['temp_selection'] = selected_cand
                    st.rerun() # Force Rerun to switch to Selection Confirmation UI immediately
            
            elif not st.session_state.get('manual_entry_mode'):
                # Empty State (No Search, No Manual Entry)
                # Only show if NOT in confirmation mode
                if not st.session_state.get('confirm_step'):
                    st.session_state['temp_selection'] = None
                    
                    # [Moved] Recently Added Section (Landing Page Only)
                    st.divider()
                    st.subheader("🆕 최근 기록 (Recently Added)")
                    
                    cached_recent = get_cached_records()
                    if cached_recent:
                        # Reverse to show newest first, take top 3
                        recent_3 = cached_recent[-3:][::-1] 
                        
                        rc1, rc2, rc3 = st.columns(3)
                        cols_recent = [rc1, rc2, rc3]
                        
                        for i, rec in enumerate(recent_3):
                            if i < 3:
                                with cols_recent[i]:
                                    with st.container(border=True):
                                        # Poster
                                        img = str(rec.get('Image', ''))
                                        if img.startswith('http'):
                                            st.image(img, use_container_width=True)
                                        else:
                                            st.markdown("## 🎬")
                                        
                                        # Title & Rating
                                        st.markdown(f"**{rec['Title']}**")
                                        r_val = float(rec['Rating']) if rec['Rating'] else 0.0
                                        st.markdown(f"<span style='color:orange'>{get_star_string(r_val)}</span>", unsafe_allow_html=True)
                                        st.caption(f"{rec['Date']}")
                
            # Manual Entry Form (Toggled by the '+' button)
            if st.session_state.get('manual_entry_mode'):
                st.divider()
                with st.container(border=True):
                    st.subheader("📝 직접 입력 (Manual Entry)")
                    
                    with st.form("manual_entry_form"):
                        m_title = st.text_input("제목", placeholder="작품명 입력")
                        m_platform_list = st.multiselect("플랫폼 (복수 선택 가능)", ["Cinema", "Netflix", "Disney+", "Watcha", "Wavve", "TVING", "Apple TV+", "Amazon Prime", "Coupang Play", "Other"], default=["Cinema"])
                        m_platform = ", ".join(m_platform_list)
                        m_date = st.date_input("개봉/방영일", value=datetime.now())
                        m_cast = st.text_input("감독/출연진", placeholder="예: 봉준호, 송강호")
                        m_img_url = st.text_input("포스터 이미지 URL (선택)", placeholder="https://...")
                        
                        m_submit = st.form_submit_button("수동 저장 💾")
                        
                        if m_submit and m_title:
                            # Construct Fake TMDB Object
                            fake_tmdb = {
                                "title": m_title,
                                "poster_url": m_img_url if m_img_url else "",
                                "platform": m_platform,
                                "release_date": m_date.strftime("%Y-%m-%d"),
                                "running_time": 0,
                                "cast_crew": m_cast,
                                "tmdb_id": f"manual_{datetime.now().timestamp()}",
                                "media_type": "manual",
                                "genre_ids": []
                            }
                            
                            # Prepare Pending Data
                            st.session_state['pending_data'] = {
                                'user_title': m_title,
                                'comment': "", # Use empty default
                                'date': m_date,
                                'tmdb': fake_tmdb 
                            }
                            
                            # Duplicate Check (Name based)
                            records = get_cached_records()
                            all_titles = [r['Title'] for r in records]
                            
                            if m_title in all_titles:
                                 df_existing = pd.DataFrame(records)
                                 idx = df_existing[df_existing['Title'] == m_title].index[0]
                                 st.session_state['duplicate_info'] = {
                                    'index': idx,
                                    'row_idx': idx + 2,
                                    'old_comment': df_existing.iloc[idx]['Comment'],
                                    'old_rating': pd.to_numeric(df_existing.iloc[idx]['Rating'], errors='coerce'),
                                    'old_image': df_existing.iloc[idx]['Image']
                                 }
                            else:
                                 st.session_state['duplicate_info'] = None
                                 
                            st.session_state['confirm_step'] = True
                            st.rerun()

        # Fallback: Manual Submit (검색 퀄리티가 안 좋거나 직접 입력 원할 때) - Legacy Button Removal or Hide
        # if input_title and st.button("🔎 검색 결과가 없나요? 강제 저장 시도"): ... (Removed in favor of clear Manual Entry)
    if st.session_state['confirm_step']:
        pending = st.session_state['pending_data']
        dup_info = st.session_state['duplicate_info']
        tmdb = pending['tmdb']
        
        st.info(f"💾 **'{tmdb['title']}'** (원제: {pending['user_title']}) 저장 준비 중...")

        if dup_info:
            st.warning(f"⚠️ **이미 존재하는 작품입니다!**")
            
            # --- 썸네일 비교 UI ---
            st.write("🖼️ **썸네일 선택**")
            cols = st.columns(2)
            
            old_img = dup_info.get('old_image')
            new_img = tmdb.get('poster_url')
            
            with cols[0]:
                st.caption("기존 썸네일")
                if old_img and str(old_img).startswith('http'):
                    st.image(old_img, width=120)
                else:
                    st.markdown("## 🚫 없음")
            
            with cols[1]:
                st.caption(f"새 썸네일 (TMDB)")
                if new_img and str(new_img).startswith('http'):
                    st.image(new_img, width=120)
                else:
                    st.markdown("## 🚫 없음")

            # 썸네일 선택 로직
            image_options = []
            if old_img: image_options.append("기존 이미지 유지")
            if new_img: image_options.append("새 이미지 적용")
            
            default_idx = 0
            if new_img and "새 이미지 적용" in image_options:
                default_idx = image_options.index("새 이미지 적용")
            elif old_img:
                default_idx = image_options.index("기존 이미지 유지")
                
            selected_image_opt = st.radio("어떤 이미지를 사용할까요?", image_options, index=default_idx) if image_options else None

            st.divider()
            st.write(f"기존 코멘트: {dup_info['old_comment']}")
            st.write(f"기존 별점: {dup_info['old_rating']}")
            st.caption(f"ℹ️ 새로 업데이트될 정보: {tmdb['release_date']} 개봉 | {tmdb['platform']} | {tmdb['cast_crew']}")
            
            action = st.radio("처리 방식 선택", ["✅ 합치기 (Merge)", "🔄 덮어쓰기 (Replace)", "❌ 취소 (Cancel)"], index=0)
            
            # AI 예측 실행 (여기서 미리 실행)
            if 'ai_predicted_rating' not in st.session_state:
                with st.spinner("AI가 학습 데이터(Few-Shot)를 분석하고 평점을 계산 중입니다..."):
                    st.session_state['examples_log'] = get_recent_examples() # 로그용 저장
                    st.session_state['ai_predicted_rating'] = analyze_rating_only(pending['comment'], st.session_state['examples_log'])

            # --- 🛠️ 수정 및 확인 단계 (Human-in-the-loop) ---
            with st.container(border=True):
                st.subheader("🎯 최종 평점 확인")
                
                # [UI Upgrade] 썸네일 & 메타데이터 미리보기
                c_img, c_info = st.columns([1, 4])
                with c_img:
                    if tmdb.get('poster_url'):
                        st.image(tmdb['poster_url'], use_container_width=True)
                    else:
                        st.write("🖼️")
                with c_info:
                    st.markdown(f"**{tmdb['title']}** ({tmdb['release_date'][:4] if tmdb['release_date'] else 'N/A'})")
                    # [Fix] Editable Platform (User Request)
                    st.caption("시청 플랫폼 (수정 가능)")
                    # Platform Multi-Select Logic
                    current_pl = tmdb.get('platform', 'Cinema')
                    pre_selected = [p.strip() for p in current_pl.split(',')] if current_pl else ["Cinema"]
                    p_options = ["Cinema", "Netflix", "Disney+", "Watcha", "Wavve", "TVING", "Apple TV+", "Amazon Prime", "Coupang Play", "Other"]
                    # Ensure pre-selected items are in options (handle custom inputs)
                    for p in pre_selected:
                        if p not in p_options: p_options.append(p)
                        
                    st.multiselect("플랫폼", options=p_options, default=pre_selected, label_visibility="collapsed", key="final_platform_selections")
                    st.caption(f"{tmdb['cast_crew'][:50]}...")
                    if 'comment' in pending:
                         st.write(f"📝 *\"{pending['comment']}\"*")
                
                # Process Log (API 사용 내역 투명화)
                with st.expander("🤖 AI 분석 로그 (Step-by-Step)", expanded=False):
                    st.write("1. **TMDB 검색**: 메타데이터 확보 완료")
                    examples = st.session_state.get('examples_log', "")
                    st.write(f"2. **DB 조회**: 최근 리뷰 {5 if examples else 0}개 학습 완료")
                    st.code(examples if examples else "No history yet", language="text")
                    st.write(f"3. **AI 예측**: 리뷰 톤 분석 결과 -> {st.session_state['ai_predicted_rating']}점")

                c_slide, c_btn = st.columns([3, 1])
                with c_slide:
                    # 사용자 수정 가능한 슬라이더
                    final_user_rating = st.slider(
                        "AI 제안 평점 (수정 가능)", 
                        min_value=0.0, 
                        max_value=5.0, 
                        value=float(st.session_state['ai_predicted_rating']), 
                        step=0.5,
                        format="%.1f"
                    )
                
                with c_btn:
                    st.write("") # Spacer
                    st.write("")
                    confirm_save = st.button("최종 저장 ✅", key="save_dup", use_container_width=True)

            if confirm_save:
                if "취소" in action:
                    st.session_state['confirm_step'] = False
                    st.session_state.pop('ai_predicted_rating', None) # 초기화
                    st.error("취소되었습니다.")
                    st.rerun()

                with st.spinner("DB에 저장 중..."):
                    new_rating = final_user_rating
                    
                    final_date = pending['date'].strftime("%Y-%m-%d") if pending['date'] else (tmdb['release_date'] or datetime.now().strftime("%Y-%m-%d"))
                    
                    # 최종 이미지
                    final_image_url = ""
                    if selected_image_opt == "새 이미지 적용": final_image_url = new_img
                    elif selected_image_opt == "기존 이미지 유지": final_image_url = old_img
                    else: final_image_url = ""

                    final_rating = new_rating
                    final_comment = pending['comment']
                    
                    if "합치기" in action:
                        old_r = dup_info['old_rating'] if not pd.isna(dup_info['old_rating']) else 0.0
                        final_rating = (old_r + new_rating) / 2
                        final_comment = f"{dup_info['old_comment']} -> {pending['comment']}"

                    # 데이터 구성
                    row_data = [
                        final_date,
                        tmdb['title'], # TMDB의 정확한 제목 사용
                        ", ".join(st.session_state.get('final_platform_selections', [])), # [Fix] Use Edited Platform (multiselect joined)
                        final_rating,
                        final_comment,
                        tmdb['release_date'],
                        final_image_url,
                        tmdb['running_time'],
                        tmdb['cast_crew']
                    ]
                    
                    sheet = get_sheet_connection()
                    range_name = f"A{dup_info['row_idx']}:I{dup_info['row_idx']}"
                    sheet.update(range_name, [row_data])
                    clear_sheet_cache() # 데이터 변경 캐시 초기화
                    
                    st.success(f"처리 완료! ({action})")
                    st.session_state['confirm_step'] = False
                    st.rerun()
                        
        else:
            # 중복 아님 - 신규 저장
            
            # AI 예측 실행 (여기서 미리 실행)
            if 'ai_predicted_rating' not in st.session_state:
                with st.spinner("AI가 학습 데이터(Few-Shot)를 분석하고 평점을 계산 중입니다..."):
                    st.session_state['examples_log'] = get_recent_examples() # 로그용 저장
                    st.session_state['ai_predicted_rating'] = analyze_rating_only(pending['comment'], st.session_state['examples_log'])

            # --- 🛠️ 수정 및 확인 단계 (Human-in-the-loop) ---
            with st.container(border=True):
                st.subheader("🎯 최종 평점 확인")
                
                # Process Log
                with st.expander("🤖 AI 분석 로그 (Step-by-Step)", expanded=False):
                    st.write("1. **TMDB 검색**: 메타데이터 확보 완료")
                    examples = st.session_state.get('examples_log', "")
                    st.write(f"2. **DB 조회**: 최근 리뷰 {5 if examples else 0}개 학습 완료")
                    st.code(examples if examples else "No history yet", language="text")
                    st.write(f"3. **AI 예측**: 리뷰 톤 분석 결과 -> {st.session_state['ai_predicted_rating']}점")

                c_slide, c_btn = st.columns([3, 1])
                with c_slide:
                    final_user_rating = st.slider(
                        "AI 제안 평점 (수정 가능)", 
                        min_value=0.0, 
                        max_value=5.0, 
                        value=float(st.session_state['ai_predicted_rating']), 
                        step=0.5,
                        format="%.1f",
                        key="new_rating_slider"
                    )
                
                with c_btn:
                    st.write("") 
                    st.write("")
                    confirm_save_new = st.button("기록하기 (최종) ✅", use_container_width=True)

            if confirm_save_new:
                with st.spinner("DB에 저장 중..."):
                    new_rating = final_user_rating
                    
                    final_date = pending['date'].strftime("%Y-%m-%d") if pending['date'] else (tmdb['release_date'] or datetime.now().strftime("%Y-%m-%d"))
                    
                    row_data = [
                        final_date,
                        tmdb['title'],
                        st.session_state.get('final_platform_input', tmdb['platform']), # [Fix] Use Edited Platform
                        new_rating,
                        pending['comment'],
                        tmdb['release_date'],
                        tmdb['poster_url'],
                        tmdb['running_time'],
                        tmdb['cast_crew']
                    ]
                    
                    sheet = get_sheet_connection()
                    sheet.append_row(row_data)
                    clear_sheet_cache() # 데이터 변경 캐시 초기화
                    
                    st.success(f"저장 완료! ({get_star_string(new_rating)})")
                    st.session_state.pop('ai_predicted_rating', None) # 초기화
                    
                    # --- 추천 로직 시작 ---
                    # 현재 저장된 모든 타이틀 가져오기 (필터링용)
                    # 캐시 사용 (위에서 clear 했으니 다시 갱신됨)
                    records = get_cached_records()
                    all_titles_for_rec = [r['Title'] for r in records] 
                    
                    rec_item = get_recommendation(tmdb, new_rating, existing_titles=all_titles_for_rec)
                    if rec_item:
                        st.session_state['recommendation_candidate'] = rec_item
                        st.session_state['confirm_step'] = False # 중요: 추천 모드로 갈 때 입력 폼 상태 초기화
                        st.rerun()
                    else:
                        st.toast("추천할만한 비슷한 작품이 없거나, 이미 리스트에 있습니다. 😎")
                    
                    st.session_state['confirm_step'] = False
                    st.rerun()



# [탭 2] 찜 목록 (Wishlist)
with tab2:
    if st.button("새로고침 🔄", key="refresh_wish"): 
        clear_sheet_cache()
        st.rerun()
        
    try:
        records = get_cached_records()
        df = pd.DataFrame(records)
        if not df.empty:
            # 찜 목록 필터링
            wishlist_df = df[df['Comment'].astype(str).str.contains(r'\[찜\]', na=False)]
            
            if wishlist_df.empty:
                st.info("아직 찜한 작품이 없습니다. 추천 화면에서 '찜'을 눌러보세요!")
            else:
                st.markdown(f"### 📌 나중에 볼 작품들 ({len(wishlist_df)}편)")
                st.caption("언젠가 꼭 챙겨볼 명작들입니다.")
                
                # 갤러리 그리드
                w_cols = st.columns(4)
                for idx, row in wishlist_df.iterrows():
                    c = w_cols[idx % 4]
                    with c:
                         if row['Image'] and str(row['Image']).startswith('http'):
                             st.image(row['Image'], use_container_width=True)
                         else:
                             st.markdown("🎬")
                         st.markdown(f"**{row['Title']}**")
                         st.caption(f"{row['Platform']} | {row['RunningTime']}분")

    except Exception as e:
        st.error(f"데이터 로드 중 오류: {e}")

# [탭 3] 통계
with tab3:
    if st.button("새로고침 🔄", key="refresh_stats"): 
        clear_sheet_cache()
        st.rerun()
    try:
        # 캐시 사용
        records = get_cached_records()
        df = pd.DataFrame(records)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
            if 'RunningTime' not in df.columns: df['RunningTime'] = 0
            if 'CastCrew' not in df.columns: df['CastCrew'] = ""
            # [Data Filtering] 찜/관심없음 데이터 제외하고 분석
            # 원본 df는 유지하되, 통계용 df_stats 분리
            # 1. 찜 목록 별도 추출
            wishlist_df = df[df['Comment'].astype(str).str.contains(r'\[찜\]', na=False)]
            
            # 2. 통계용 (찜, 관심없음 제외)
            df_stats = df[~df['Comment'].astype(str).str.contains(r'\[찜\]|\[관심없음\]', na=False)].copy()
            
            # 아래 로직은 df_stats 사용
            df = df_stats # 편의상 덮어쓰기 (화면 하단 로그도 적용되도록)
            
            # RunningTime 숫자 변환
            df['RunningTime'] = pd.to_numeric(df['RunningTime'], errors='coerce').fillna(0)

            st.markdown("### 📊 Dashboard")
            
            # --- 정렬 옵션 추가 ---
            sort_opt = st.radio("정렬 기준", ["최신 관람일순 (Date)", "최신 기록순 (Input)", "별점 높은순", "별점 낮은순"], horizontal=True)
            
            filter_option = st.radio("기간 선택", ["전체 누적", "올해 (2025)"], horizontal=True) 
            target_df = df[df['Date'].dt.year == datetime.now().year] if filter_option == "올해 (2025)" else df

            # 정렬 로직 적용
            if "별점 높은순" in sort_opt:
                target_df = target_df.sort_values(by=["Rating", "Date"], ascending=[False, False])
            elif "별점 낮은순" in sort_opt:
                target_df = target_df.sort_values(by=["Rating", "Date"], ascending=[True, False])
            elif "최신 기록순" in sort_opt:
                 # 기록순은 Index 역순 (최근에 추가된게 맨 뒤에 있으므로)
                 target_df = target_df.sort_index(ascending=False)
            else: # 최신 관람일순
                 target_df = target_df.sort_values(by="Date", ascending=False)

            if not target_df.empty:
                # ... (Metrics Existing Code) ...
                total_min = target_df['RunningTime'].sum()
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("총 편수", f"{len(target_df)}편")
                m2.metric("총 시간", f"{int(total_min//60)}시간 {int(total_min%60)}분")
                m3.metric("평균 별점", f"{target_df['Rating'].mean():.1f}")
                
                # 최고작 (Rating -> Date 순 정렬 후 첫번째)
                best_candidates = target_df.sort_values(by=["Rating", "Date"], ascending=[False, False])
                best_title = best_candidates.iloc[0]['Title'] if not best_candidates.empty else "-"
                m4.metric("최고작", f"{best_title}")
                
                st.divider()
                
                st.divider()
                high_rated_df = target_df[target_df['Rating'] >= 4.0]
                all_names = [name.strip() for names in high_rated_df['CastCrew'] for name in names.split(',') if name]
                if all_names:
                    counts = Counter(all_names).most_common(7)
                    cols = st.columns(len(counts))
                    for i, (n, c) in enumerate(counts):
                        cols[i].markdown(f"**{i+1}위**\n\n{n} ({c}회)")
                
                st.divider()
                st.subheader("📝 Review Log")
                # target_df = target_df.sort_values(by="Date", ascending=False) # 위에서 정렬했으므로 중복 제거
                
                # 2단 그리드 생성
                cols = st.columns(2)
                
                for i, (idx, r) in enumerate(target_df.iterrows()):
                    with cols[i % 2]:
                        with st.container(border=True): # 카드 스타일 적용
                            c1, c2 = st.columns([1, 3]) # 이미지:내용 비율 조정 (공간이 좁으므로)
                            
                            # [Fix] Thumbnail Handling
                            image_url = str(r['Image']) if r['Image'] else ""
                            with c1:
                                if image_url.startswith('http'): 
                                    st.image(image_url, use_container_width=True) # use_column_width deprecated
                                else: 
                                    st.markdown("## 🎬") 
                            
                            with c2:
                                # [Fix] Date Handling for NaT
                                date_str = "날짜 미상"
                                if not pd.isna(r['Date']):
                                     date_str = r['Date'].strftime('%Y-%m-%d')
                                
                                # Rating Safety
                                rating_val = r['Rating'] if not pd.isna(r['Rating']) else 0.0
                                
                                # 1. Title (Bolder)
                                st.markdown(f"<div style='font-weight: 700; font-size: 1.1em;'>{r['Title']}</div>", unsafe_allow_html=True)
                                
                                # 2. Comment (Thinner, Larger, No Italics)
                                if r.get('Comment'):
                                    st.markdown(f"<div style='font-weight: 300; font-size: 1.1em; margin-bottom: 5px;'>{r['Comment']}</div>", unsafe_allow_html=True)
                                    
                                # 3. Rating (Stars only)
                                st.markdown(f"<span style='color:orange'>{get_star_string(rating_val)}</span>", unsafe_allow_html=True)
                                
                                # 4. Metadata (Date | Platform | Runtime)
                                runtime_str = f"{int(r['RunningTime'])}분" if r.get('RunningTime') else ""
                                meta_parts = [date_str, r['Platform'], runtime_str]
                                meta_str = " | ".join([str(p) for p in meta_parts if p])
                                st.caption(meta_str)

                                # 5. Credits
                                if r.get('CastCrew'):
                                    st.caption(f"{r['CastCrew']}")
            else: st.warning("데이터가 없습니다.")
        else: st.info("데이터가 없습니다.")
    except Exception as e: st.error(f"오류: {e}")
