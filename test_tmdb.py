import streamlit as st
import requests
import toml
import os

def test_tmdb():
    print("Testing TMDB Configuration...")
    
    try:
        secrets = toml.load(".streamlit/secrets.toml")
        api_key = secrets.get("tmdb_api_key")
        
        if not api_key:
            print("❌ TMDB API Key missing in secrets.toml")
            return
            
        print(f"✅ Found TMDB API Key: {api_key[:5]}...")
        
        # Test basic search
        query = "오징어 게임"
        url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={query}&language=ko-KR&page=1"
        
        print(f"Querying TMDB for '{query}'...")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"✅ Status 200 OK. Found {len(results)} results.")
            
            if results:
                first = results[0]
                print(f"   First result: {first.get('name') or first.get('title')} ({first.get('media_type')})")
                poster = first.get('poster_path')
                if poster:
                    print(f"   ✅ Poster Path found: {poster}")
                    print(f"   Image URL: https://image.tmdb.org/t/p/w500{poster}")
                else:
                    print("   ⚠️ Result exists but no poster_path.")
            else:
                print("   ⚠️ No results found for query. API key works but search failed?")
        else:
            print(f"❌ API Request Failed. Status: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_tmdb()
