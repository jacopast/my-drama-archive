import toml
import base64
import binascii

try:
    secrets = toml.load(".streamlit/secrets.toml")
    private_key = secrets["gcp_service_account"]["private_key"]
    
    # Strip headers
    key_body = private_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").replace("\n", "").strip()
    
    print(f"Key length: {len(key_body)}")
    print(f"Key length % 4: {len(key_body) % 4}")
    
    try:
        base64.b64decode(key_body, validate=True)
        print("✅ Private Key is valid base64.")
    except binascii.Error as e:
        print(f"❌ Invalid base64: {e}")
        # Try to fix padding
        missing_padding = len(key_body) % 4
        if missing_padding:
            print(f"Trying to fix padding (adding {'=' * (4 - missing_padding)})...")
            fixed_key = key_body + '=' * (4 - missing_padding)
            try:
                base64.b64decode(fixed_key, validate=True)
                print("✅ Fixed padding! The key was just missing '=' characters.")
            except binascii.Error as e2:
                print(f"❌ Still invalid after padding fix: {e2}")

except Exception as e:
    print(f"Error checking key: {e}")
