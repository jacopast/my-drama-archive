from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import toml
import json

def test_auth():
    print("Testing Google Auth Configuration...")
    
    # Manually load secrets to simulate Streamlit environment if running as script
    try:
        if not hasattr(st, "secrets") or not st.secrets:
            secrets_data = toml.load(".streamlit/secrets.toml")
            # We must monkeypatch or use dict directly
            creds_dict = dict(secrets_data["gcp_service_account"])
        else:
             creds_dict = dict(st.secrets["gcp_service_account"])
             
        # IMPORTANT: Common fix for streamlit secrets is replacing literal \n with actual newline
        # if the toml parser didn't do it (escaped string).
        if "\\n" in creds_dict["private_key"]:
            print("ℹ️  Found literal \\n sequences in private key. Converting to real newlines...")
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        print("Attempting to create ServiceAccountCredentials...")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        print("✅ Credentials object created successfully!")
        
        # Optional: Try to sign a blob to verify key validity deeply (if library supports easy check)
        if creds.service_account_email:
             print(f"✅ Service Account Email: {creds.service_account_email}")
        
    except Exception as e:
        print(f"❌ Auth Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auth()
