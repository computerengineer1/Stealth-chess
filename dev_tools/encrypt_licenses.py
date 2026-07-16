import json
import base64

# Use the exact same key in licensing.py
SECRET_KEY = "STEALTH_CHESS_SECRET_KEY_2026"

def xor_encrypt_decrypt(data: str, key: str) -> str:
    """XOR encryption/decryption helper using a secret key."""
    key_len = len(key)
    output = []
    for i, char in enumerate(data):
        key_char = key[i % key_len]
        # XOR the characters and store as character
        output.append(chr(ord(char) ^ ord(key_char)))
    return "".join(output)

def encrypt_database(db_dict: dict) -> str:
    """Converts a dictionary to encrypted base64 payload."""
    json_str = json.dumps(db_dict)
    xor_str = xor_encrypt_decrypt(json_str, SECRET_KEY)
    # Encode as Base64 string for easy web transfer
    encoded_bytes = base64.b64encode(xor_str.encode('utf-8'))
    return encoded_bytes.decode('utf-8')

def decrypt_database(encoded_str: str) -> dict:
    """Decrypts a base64 payload back to dictionary."""
    decoded_bytes = base64.b64decode(encoded_str.encode('utf-8'))
    xor_str = decoded_bytes.decode('utf-8')
    json_str = xor_encrypt_decrypt(xor_str, SECRET_KEY)
    return json.loads(json_str)

if __name__ == "__main__":
    print("="*60)
    print("      Chess Bot License Database Encrypter")
    print("="*60)
    
    # 1. Define your active subscription keys
    # YYYY-MM-DD format for expiration date
    license_db = {
        "keys": {
                        "LFT-7602-6384-E520-C4BD" : {
                "tier": "Lifetime",
                "expiry": "2026-07-08",   # تاريخ الغد تلقائياً
                "hwid": "4145-3382-65EA-6926",  # بصمة كمبيوتر العميل هنا
                "mobile_hwid": ""
            },

                        "MON-54B0-1814-B5CD-A25F" : {
                "tier": "Monthly",
                "expiry": "2026-07-12",   # تاريخ الغد تلقائياً
                "hwid": "",
                "mobile_hwid": "MOB-AB6F-FF54-C455" # بصمة آيفون العميل هنا
            },

            "MON-8D6E-76B4-226F-1F46" : {
    "tier": "Monthly",
    "expiry": "2026-07-06",
    "hwid": "رمز_جهاز_الكمبيوتر",
    "mobile_hwid": "MOB-424E-C00B-6EEB"
},
"MON-3805-7684-F8A8-5BA0" : {
    "tier": "Monthly",
    "expiry": "2026-07-06",
    "hwid": "رمز_جهاز_الكمبيوتر",
    "mobile_hwid": "MOB-424E-C00B-6EEB"
},

            "MON-81D9-5EF8-957C-884C" : {
                "tier": "Monthly",
                "expiry": "2026-07-06",
                "hwid": "",          # PC lock: paste customer Machine ID here
                "mobile_hwid": ""    # Mobile lock: paste customer Device ID here (e.g., "MOB-A1B2-C3D4-E5F6")
            },
            "TRL-F622-CABA-C7C9-00BE" : {
                "tier": "Trial",
                "expiry": "2026-07-06",
                "hwid": "",
                "mobile_hwid": ""
            },
            "MON-9026-41DB-895D-121F" : {
                "tier": "Monthly",
                "expiry": "2026-08-04",
                "hwid": "",
                "mobile_hwid": ""
            },
            "MON-1033-DE2A-155C-6A5B" : { 
                "tier": "Monthly",
                "expiry": "2026-06-22",
                "hwid": "",
                "mobile_hwid": ""
            },
            "TRL-8F92-31A4-0B6B-2748" : {
                "tier": "Trial",
                "expiry": "2026-06-18",
                "hwid": "",
                "mobile_hwid": ""
            },
            "TRL-45FA-EB1D-CE7B-E369" : { 
                "tier": "Trial",
                "expiry": "2026-06-14",
                "hwid": "",
                "mobile_hwid": ""
            },
            "MON-FA5E-4026-EFF0-4456" : { 
                "tier": "Monthly",
                "expiry": "2026-06-22",
                "hwid": "",
                "mobile_hwid": ""
            },
            "TRM-93F5-138C-0C5C-4E06" : { 
                "tier": "3 Months",
                "expiry": "2026-08-22",
                "hwid": "",
                "mobile_hwid": ""
            },
            "LFT-5D17-73A5-C645-C850": {
                "tier": "Lifetime",
                "expiry": "2099-12-31",
                "hwid": "",          # Leave empty for no hardware lock, or paste Machine ID (e.g., "5E9A-3D2C-11AB")
                "mobile_hwid": ""    # Leave empty for no mobile lock, or paste Device ID (e.g., "MOB-A1B2-C3D4-E5F6")
            }
        }
    }
    
    # 2. Encrypt the database
    encrypted_payload = encrypt_database(license_db)
    
    print("\n[+] Encrypted Payload (Copy the text below):")
    print("-" * 60)
    print(encrypted_payload)
    print("-" * 60)
    
    print("\n[+] To host your database online:")
    print("1. Copy the encrypted payload text above.")
    print("2. Go to https://pastebin.com or create a private GitHub Gist.")
    print("3. Paste the text and click Save.")
    print("4. Get the Raw URL of that paste/gist (e.g. https://pastebin.com/raw/...)")
    print("5. Put that URL in c:\\Users\\mahmo\\Downloads\\chess bot\\config.py under LICENSE_API_URL")
    print("\n[+] Double check decryption works:")
    decrypted = decrypt_database(encrypted_payload)
    print(f"Decrypted successfully! Number of keys: {len(decrypted.get('keys', {}))}")
    print("="*60)
