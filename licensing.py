import os
import urllib.request
import urllib.error
import json
import base64
import datetime
import hashlib
import uuid
import subprocess
import sys

# Must match the SECRET_KEY in encrypt_licenses.py
SECRET_KEY = "STEALTH_CHESS_SECRET_KEY_2026"

def xor_encrypt_decrypt(data: str, key: str) -> str:
    """XOR encryption/decryption helper using a secret key."""
    key_len = len(key)
    output = []
    for i, char in enumerate(data):
        key_char = key[i % key_len]
        output.append(chr(ord(char) ^ ord(key_char)))
    return "".join(output)

def get_hwid() -> str:
    """Generates a stable, unique Machine ID for Windows with fallback options."""
    raw_id = ""
    if sys.platform == "win32":
        try:
            # Try to read the unique MachineGuid from Registry
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            raw_id, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
        except Exception:
            try:
                # Fallback 1: WMI BIOS UUID (avoiding flash/cmd popup using CREATE_NO_WINDOW flag)
                # 0x08000000 is CREATE_NO_WINDOW
                out = subprocess.check_output("wmic csproduct get uuid", shell=True, creationflags=0x08000000).decode()
                raw_id = out.split('\n')[1].strip()
            except Exception:
                pass
                
    if not raw_id or len(raw_id) < 5:
        # Fallback 2: Unique node MAC address hash
        raw_id = str(uuid.getnode())
        
    h = hashlib.sha256(raw_id.encode('utf-8')).hexdigest().upper()
    return f"{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"


class LicenseManager:
    """
    Manages license validation for the Chess Bot.
    Fetches an encrypted license database from a remote URL (like GitHub Gist or Pastebin),
    decrypts it, and verifies the subscription key's validity and expiration.
    """
    LICENSE_FILE = "license.key"

    def __init__(self, api_url=None):
        self.api_url = api_url
        self.license_key = ""
        self.is_valid = False
        self.expiry_date = "N/A"
        self.tier = "N/A"
        self.error_message = ""

    def load_local_key(self) -> str:
        """Loads the license key from a local file if it exists."""
        if os.path.exists(self.LICENSE_FILE):
            try:
                with open(self.LICENSE_FILE, "r", encoding="utf-8") as f:
                    self.license_key = f.read().strip()
                return self.license_key
            except Exception:
                pass
        return ""

    def save_local_key(self, key: str):
        """Saves the license key to a local file."""
        self.license_key = key.strip()
        try:
            with open(self.LICENSE_FILE, "w", encoding="utf-8") as f:
                f.write(self.license_key)
        except Exception as e:
            print(f"Error saving license key: {e}")

    def clear_local_key(self):
        """Removes the local license file."""
        if os.path.exists(self.LICENSE_FILE):
            try:
                os.remove(self.LICENSE_FILE)
            except Exception:
                pass
        self.license_key = ""
        self.is_valid = False

    def validate_key(self, key: str) -> bool:
        """
        Validates the license key against the encrypted remote database.
        Includes a local mock mode for development and testing.
        """
        key = key.strip()
        if not key:
            self.error_message = "Key cannot be empty"
            self.is_valid = False
            return False



        if not self.api_url:
            self.error_message = "No online license database configured. Configure LICENSE_API_URL in config.py."
            self.is_valid = False
            return False

        # --- Online Database Validation ---
        try:
            # Fetch the encrypted database payload from the raw Pastebin/Gist URL
            req = urllib.request.Request(
                self.api_url,
                headers={"User-Agent": "ChessBot-Licensing-Client"}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                payload = response.read().decode('utf-8').strip()
                
            # Decrypt the database
            decoded_bytes = base64.b64decode(payload.encode('utf-8'))
            xor_str = decoded_bytes.decode('utf-8')
            json_str = xor_encrypt_decrypt(xor_str, SECRET_KEY)
            db = json.loads(json_str)
            
            keys_dict = db.get("keys", {})
            
            if key not in keys_dict:
                self.error_message = "Invalid license key"
                self.is_valid = False
                return False
                
            key_info = keys_dict[key]
            expiry_str = key_info.get("expiry", "2026-05-22")
            tier_str = key_info.get("tier", "Active")
            allowed_hwid = key_info.get("hwid", "")
            
            if allowed_hwid and allowed_hwid.strip() != "":
                current_hwid = get_hwid()
                if allowed_hwid.strip().upper() != current_hwid.upper():
                    self.error_message = "Hardware lock mismatch. Key is registered to another device."
                    self.is_valid = False
                    return False
            
            # Parse date and verify
            expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d").date()
            current_date = datetime.date.today()
            
            if current_date > expiry_date:
                self.error_message = f"Subscription expired on {expiry_str}"
                self.is_valid = False
                return False
                
            self.is_valid = True
            self.tier = tier_str
            self.expiry_date = expiry_str
            self.save_local_key(key)
            return True
                    
        except urllib.error.URLError as e:
            self.error_message = f"Connection failed: {e.reason}"
            self.is_valid = False
            return False
        except Exception as e:
            self.error_message = f"Failed to decrypt database or invalid format"
            self.is_valid = False
            return False
