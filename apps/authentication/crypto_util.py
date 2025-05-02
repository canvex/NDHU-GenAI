import base64
import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from dotenv import load_dotenv

# 讀取 .env 檔案
load_dotenv()

# 從環境變數取得密鑰
secret_key = os.environ.get("AES_SECRET_KEY")
if not secret_key:
    raise ValueError("AES_SECRET_KEY not found in environment.")
if len(secret_key.encode('utf-8')) != 32:
    raise ValueError("AES_SECRET_KEY must be exactly 32 bytes long.")

SECRET_KEY = secret_key.encode('utf-8')

def encrypt(plain_text):
    if plain_text is None:
        return None
    plain_text = plain_text.encode('utf-8')
    iv = get_random_bytes(16)  # 產生隨機 IV
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
    ct_bytes = cipher.encrypt(pad(plain_text, AES.block_size))
    return base64.b64encode(iv + ct_bytes).decode('utf-8')

def decrypt(cipher_text):
    if cipher_text is None:
        return None
    raw = base64.b64decode(cipher_text)
    iv = raw[:16]
    ct = raw[16:]
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    return pt.decode('utf-8')
