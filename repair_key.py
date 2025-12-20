import toml
import base64
from pyasn1_modules import pem, rfc2437
from pyasn1.codec.der import decoder

def repair_key():
    try:
        data = toml.load(".streamlit/secrets.toml")
        pk = data["gcp_service_account"]["private_key"]
        
        # Strip to pure base64
        clean_pk = pk.replace("\n", "").replace("\\n", "") \
                     .replace("-----BEGIN PRIVATE KEY-----", "") \
                     .replace("-----END PRIVATE KEY-----", "").strip()
        
        # We know clean_pk ends in '===' or '==' currently, and has length issue.
        # Let's remove the tail chars that are problematic and try variants.
        # We suspect the last few chars are "9Ww". And we have too many chars (1 mod 4 remainder in data? or 5 chars in last block).
        
        # Let's clean the padding first
        clean_pk = clean_pk.rstrip('=')
        
        print(f"Base length (no padding): {len(clean_pk)}")
        print(f"Tail: ...{clean_pk[-10:]}")
        
        # Candidates to try:
        # 1. Remove last char
        # 2. Remove 2nd to last char
        # 3. Remove 3rd to last char
        
        candidates = []
        candidates.append(clean_pk) # Maybe just needs correct padding?
        candidates.append(clean_pk[:-1]) # Remove last char
        candidates.append(clean_pk[:-2] + clean_pk[-1]) # Remove 2nd last
        candidates.append(clean_pk[:-3] + clean_pk[-2:]) # Remove 3rd last
        
        found_valid = None
        
        for i, cand in enumerate(candidates):
            # Pad correctly
            missing = len(cand) % 4
            if missing:
                padded = cand + '=' * (4 - missing)
            else:
                padded = cand
                
            try:
                key_bytes = base64.b64decode(padded, validate=True)
                # Try to decode as RSA Key (PKCS#8 usually for GCP)
                # GCP keys are usually PKCS8 PrivateKeyInfo
                # Let's try to just decode structure.
                try:
                    decoder.decode(key_bytes)
                    print(f"✅ Candidate {i} is VALID DER structure!")
                    found_valid = padded
                    break
                except Exception as e:
                    print(f"Candidate {i} is valid base64 but invalid DER: {e}")
            except Exception as e:
                print(f"Candidate {i} is invalid base64: {e}")

        if found_valid:
            print("Repair successful. Saving...")
            
            # Reformat to single line with \n
            formatted_key = "-----BEGIN PRIVATE KEY-----\\n"
            chunks = [found_valid[i:i+64] for i in range(0, len(found_valid), 64)]
            formatted_key += "\\n".join(chunks)
            formatted_key += "\\n-----END PRIVATE KEY-----\\n"
            
            data["gcp_service_account"]["private_key"] = formatted_key
            with open(".streamlit/secrets.toml", "w") as f:
                toml.dump(data, f)
            print("💾 secrets.toml updated.")
            
        else:
            print("❌ Could not repair key automatically.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    repair_key()
