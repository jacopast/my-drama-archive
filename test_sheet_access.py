import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import toml

def test_sheet():
    print("Testing Google Sheet 'media_db' Access...")
    try:
        # Load secrets
        if not hasattr(st, "secrets") or not st.secrets:
            secrets_data = toml.load(".streamlit/secrets.toml")
            creds_dict = dict(secrets_data["gcp_service_account"])
        else:
            creds_dict = dict(st.secrets["gcp_service_account"])
            
        # Fix newlines if needed
        if "\\n" in creds_dict["private_key"]:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        print("✅ Client authorized.")
        
        # Try to open the sheet
        sheet = client.open("media_db").sheet1
        print("✅ Successfully opened 'media_db' (sheet1).")
        
        # Try to read one record to confirm read access
        val = sheet.cell(1, 1).value
        print(f"✅ Read A1 cell value: {val}")
        
    except gspread.exceptions.SpreadsheetNotFound:
        print("❌ Error: Spreadsheet 'media_db' not found. Check if the Service Account email is added as an Editor.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sheet()
