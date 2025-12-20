import toml
import groq
import os

print("1. 비밀번호 파일(.streamlit/secrets.toml) 읽는 중...")
try:
    secrets = toml.load(".streamlit/secrets.toml")
    if "groq_api_key" not in secrets:
        print("❌ 실패: secrets.toml 파일에 'groq_api_key'가 없습니다.")
        exit(1)
    
    api_key = secrets["groq_api_key"]
    print("✅ 성공: 키를 찾았습니다.")
except Exception as e:
    print(f"❌ 실패: 파일을 읽을 수 없습니다. {e}")
    exit(1)

print("2. Groq AI 서버에 연결 시도 중...")
try:
    client = groq.Groq(api_key=api_key)
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": "짧게 '연결 성공!' 이라고만 말해줘."}],
        model="llama-3.3-70b-versatile",
    )
    print(f"✅ AI 응답: {chat_completion.choices[0].message.content}")
except Exception as e:
    print(f"❌ AI 연결 실패: {e}")
