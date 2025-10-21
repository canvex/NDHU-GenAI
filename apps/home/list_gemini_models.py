import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ 環境變數 GOOGLE_API_KEY 未設定")
else:
    genai.configure(api_key=api_key)
    print("✅ GOOGLE_API_KEY 已設定，正在嘗試列出可用模型...")
    try:
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                print(f"模型名稱: {m.name}, 支援方法: {m.supported_generation_methods}")
    except Exception as e:
        print(f"❌ 列出模型時發生錯誤: {e}")
        print("請檢查您的 GOOGLE_API_KEY 是否正確，以及網路連線是否正常。")
