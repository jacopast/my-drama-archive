import pandas as pd
import toml
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
import gspread

def remove_duplicates():
    print("🧹 Cleaning up duplicates...")
    
    # Auth Logic (Mirrored from test_auth)
    try:
        # Load secrets safely
        try:
            secrets_data = toml.load(".streamlit/secrets.toml")
            creds_dict = dict(secrets_data["gcp_service_account"])
        except:
            # Fallback for when running in streamlit context? No, this is script.
            print("❌ Cannot load .streamlit/secrets.toml")
            return

        if "\\n" in creds_dict["private_key"]:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open("media_db").sheet1
        
        # Read Data
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        initial_count = len(df)
        print(f"📊 Current Total Records: {initial_count}")
        
        if df.empty:
            print("Empty sheet, nothing to do.")
            return

        # Deduplicate
        # keep='first' -> keeps the top-most (oldest entry usually, if appended)
        # But user said "dozens added recently". Those are likely at bottom.
        # Actually standard append adds to bottom.
        # So keep='first' keeps the ORIGINAL if it existed before the spam. perfect.
        df_dedup = df.drop_duplicates(subset=['Title'], keep='first')
        
        final_count = len(df_dedup)
        removed_count = initial_count - final_count
        
        print(f"📉 Records after cleanup: {final_count}")
        print(f"🗑️ Duplicates removed: {removed_count}")
        
        if removed_count > 0:
            # Write back
            # Clear sheet
            sheet.clear()
            # Prepare data (Header + Values)
            # gspread update needs list of lists
            # Header
            header = df_dedup.columns.values.tolist()
            # Values
            values = df_dedup.values.tolist()
            
            sheet.update([header] + values)
            print("✅ Sheet successfully updated!")
        else:
            print("✅ No duplicates found.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    remove_duplicates()
