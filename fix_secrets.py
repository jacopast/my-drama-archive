import toml

def fix_secrets():
    try:
        data = toml.load(".streamlit/secrets.toml")
        
        # 1. Fix Private Key Format
        if "gcp_service_account" in data and "private_key" in data["gcp_service_account"]:
            pk = data["gcp_service_account"]["private_key"]
            # Remove any existing newlines and ensure standard format
            clean_pk = pk.replace("\n", "").replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()
            
            # Reconstruct with standard headers and explicit \n
            # This is the most reliable format for streamlit secrets
            # We want: "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
            # But represented as a single line string with \n literals for the toml
            
            # Actually, let's just make it a single line with \n characters escaping the real newlines
            # First, check if valid base64
            import base64
            import binascii
            
            try:
                base64.b64decode(clean_pk, validate=True)
                print("✅ Key content is valid base64 (stripped).")
            except binascii.Error:
                print("❌ Key content is INVALID base64. Padding/Length issue.")
                missing = len(clean_pk) % 4
                if missing:
                    clean_pk += '=' * (4 - missing)
                    print(f"   Attempting to fix padding by adding {4-missing} '=' chars.")
            
            # Format nicely for the file: Single line with \n is safest for TOML + Streamlit
            # But to ensure it works, we usually put `\n` literals.
            
            formatted_key = "-----BEGIN PRIVATE KEY-----\\n"
            # Split into 64 char chunks for standard PEM formatting
            chunks = [clean_pk[i:i+64] for i in range(0, len(clean_pk), 64)]
            formatted_key += "\\n".join(chunks)
            formatted_key += "\\n-----END PRIVATE KEY-----\\n"
            
            data["gcp_service_account"]["private_key"] = formatted_key
            print("✅ Re-formatted private key to single-line with \\n escapes.")

        # 2. Write back to file
        with open(".streamlit/secrets.toml", "w") as f:
            toml.dump(data, f)
        
        # TOML library might have escaped the backslashes doubly. Let's read and check or just write manually if needed.
        # Actually, toml.dump might write literal newlines for multiline strings if we aren't careful.
        # Let's force it to be a simple string.
        
        print("💾 Saved corrected secrets.toml")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_secrets()
