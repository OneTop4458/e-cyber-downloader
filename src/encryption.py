# --- 파일명: encryption.py ---
import os
from cryptography.fernet import Fernet

def load_or_generate_key():
    key_file = "secret.key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
    return key

FERNET_KEY = load_or_generate_key()
fernet = Fernet(FERNET_KEY)
