import toml
import base64
import binascii

def analyze_length():
    try:
        data = toml.load(".streamlit/secrets.toml")
        pk = data["gcp_service_account"]["private_key"]
        
        clean_pk = pk.replace("\n", "").replace("\\n", "") \
                     .replace("-----BEGIN PRIVATE KEY-----", "") \
                     .replace("-----END PRIVATE KEY-----", "").strip()
        
        # Take the first 100 chars to decode header
        # Base64 decode safely
        header_b64 = clean_pk[:100]
        header_bytes = base64.b64decode(header_b64)
        
        # Parse DER length
        # First byte is 0x30 (SEQUENCE)
        # Second byte is length (if < 128) or length-of-length (if > 128)
        
        print(f"First byte: {hex(header_bytes[0])}")
        
        length_byte = header_bytes[1]
        print(f"Length byte: {hex(length_byte)}")
        
        total_len = 0
        header_len = 0
        
        if length_byte < 128:
            total_len = length_byte
            header_len = 2
        else:
            num_len_bytes = length_byte & 0x7F
            print(f"Length bytes count: {num_len_bytes}")
            len_bytes = header_bytes[2 : 2 + num_len_bytes]
            total_len = int.from_bytes(len_bytes, byteorder='big')
            header_len = 2 + num_len_bytes
            
        print(f"Declared ASN.1 Data Length: {total_len} bytes")
        print(f"Total Expected Bytes (Header + Data): {total_len + header_len}")
        
        expected_b64_chars = ((total_len + header_len) * 4 + 2) // 3
        # Round up to multiple of 4 for padding
        if expected_b64_chars % 4 != 0:
            expected_b64_chars += (4 - (expected_b64_chars % 4))
            
        print(f"Estimated Base64 String Length: {expected_b64_chars}")
        print(f"Current Base64 String Length (unpadded): {len(clean_pk)}")
        
    except Exception as e:
        print(f"Analysis failed: {e}")

if __name__ == "__main__":
    analyze_length()
