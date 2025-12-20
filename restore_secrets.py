import toml

def restore_secrets():
    try:
        data = toml.load(".streamlit/secrets.toml")
        pk = data["gcp_service_account"]["private_key"]
        
        # Clean up my previous mess (===)
        # And ensure standard formatting
        clean_pk = pk.replace("\n", "").replace("\\n", "") \
                     .replace("-----BEGIN PRIVATE KEY-----", "") \
                     .replace("-----END PRIVATE KEY-----", "").strip()

        # Enforce max 2 padding
        clean_pk = clean_pk.rstrip('=')
        # Add standard valid padding for the current length (even if data is short, make it valid base64)
        m = len(clean_pk) % 4
        if m:
            clean_pk += '=' * (4 - m)
            
        # Reformat
        formatted_key = "-----BEGIN PRIVATE KEY-----\\n"
        chunks = [clean_pk[i:i+64] for i in range(0, len(clean_pk), 64)]
        formatted_key += "\\n".join(chunks)
        formatted_key += "\\n-----END PRIVATE KEY-----\\n"
        
        data["gcp_service_account"]["private_key"] = formatted_key
        
        with open(".streamlit/secrets.toml", "w") as f:
            toml.dump(data, f)
            
        print("✅ Restored secrets.toml to valid base64 format (though data is likely still truncated).")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    restore_secrets()
