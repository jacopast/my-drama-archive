import toml
import os

def check_secrets():
    secrets_path = ".streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
        print("❌ secrets.toml not found!")
        return

    try:
        secrets = toml.load(secrets_path)
        print("✅ secrets.toml loaded successfully.")
    except Exception as e:
        print(f"❌ Error loading toml: {e}")
        return

    # 1. Check GCP Service Account
    if "gcp_service_account" not in secrets:
        print("❌ 'gcp_service_account' section missing.")
    else:
        gcp = secrets["gcp_service_account"]
        
        # Check Private Key
        pk = gcp.get("private_key")
        if not pk:
            print("❌ 'private_key' is missing in gcp_service_account.")
        else:
            print(f"ℹ️ Private Key found. Length: {len(pk)}")
            if "\\n" in pk:
                print("⚠️  Warning: Private key contains literal '\\n' strings. These likely need to be actual newlines.")
            if "\n" in pk:
                print("ℹ️  Private key contains actual newline characters.")
            
            # Simple header check
            if "-----BEGIN PRIVATE KEY-----" not in pk:
                print("❌ Private key is missing the standard header.")
            else:
                print("✅ Private key has standard header.")
                
            # Content check (safe)
            raw_key = pk.replace("\\n", "\n")
            lines = raw_key.strip().split('\n')
            print(f"ℹ️  Key has {len(lines)} lines (after converting \\n to newlines if present).")
            if len(lines) < 5:
                 print("⚠️  Key seems too short (few lines). formatting might be collapsed.")

    # 2. Check Groq API Key
    groq_key = secrets.get("groq_api_key")
    if not groq_key:
        print("❌ 'groq_api_key' is missing.")
    else:
        print(f"✅ 'groq_api_key' present. Starts with: {groq_key[:4]}...")

    # 3. Check TMDB API Key
    tmdb_key = secrets.get("tmdb_api_key")
    if not tmdb_key:
        print("❌ 'tmdb_api_key' is missing.")
    else:
        print(f"✅ 'tmdb_api_key' present. Length: {len(tmdb_key)}")

if __name__ == "__main__":
    check_secrets()
