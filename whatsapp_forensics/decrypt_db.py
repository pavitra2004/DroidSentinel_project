import subprocess
import sys
import os

def decrypt_whatsapp_db(key_path, crypt_path, output_path="msgstore.db"):
    """
    Decrypts WhatsApp .crypt14 or .crypt15 database file.
    
    key_path   = path to 'key' file extracted from phone/emulator
    crypt_path = path to msgstore.db.crypt14 or .crypt15
    output_path = where to save the decrypted database
    """
    if not os.path.exists(key_path):
        print(f"[!] Key file not found: {key_path}")
        return False
    
    if not os.path.exists(crypt_path):
        print(f"[!] Encrypted database not found: {crypt_path}")
        return False

    try:
        from wa_crypt_tools.lib.db.db14 import Database14
        from wa_crypt_tools.lib.key.keyfactory import KeyFactory

        print(f"[*] Reading key file: {key_path}")
        with open(key_path, "rb") as f:
            key = KeyFactory.new(f.read())

        print(f"[*] Decrypting: {crypt_path}")
        with open(crypt_path, "rb") as encrypted:
            db = Database14(key, encrypted)
            with open(output_path, "wb") as decrypted:
                db.decrypt(encrypted, decrypted)

        print(f"[✓] Decrypted successfully → {output_path}")
        return True

    except Exception as e:
        print(f"[!] Decryption error: {e}")
        print("[*] Trying command line method...")
        
        result = subprocess.run(
            [sys.executable, "-m", "wa_crypt_tools.decrypt14",
             key_path, crypt_path, output_path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"[✓] Decrypted successfully → {output_path}")
            return True
        else:
            print(f"[!] Failed: {result.stderr}")
            return False


if __name__ == "__main__":
    # ── CHANGE THESE PATHS ──────────────────────────────
    KEY_PATH   = "key"                      # your key file
    CRYPT_PATH = "msgstore.db.crypt14"      # your encrypted db
    OUT_PATH   = "msgstore.db"              # output decrypted db
    # ────────────────────────────────────────────────────
    
    decrypt_whatsapp_db(KEY_PATH, CRYPT_PATH, OUT_PATH)