import os
import json
import base64
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
from io import BytesIO

# 載入環境變數
load_dotenv()

def extract_fields_from_image_gemini(image_path):
    # 從環境變數讀取 API Key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("❌ 環境變數 GOOGLE_API_KEY 未設定")

    genai.configure(api_key=api_key)

    # 載入圖片
    try:
        img = Image.open(image_path)
    except FileNotFoundError:
        print(f"❌ 圖片檔案未找到: {image_path}")
        return {"error": f"圖片檔案未找到: {image_path}"}
    except Exception as e:
        print(f"❌ 載入圖片失敗: {str(e)}")
        return {"error": f"載入圖片失敗: {str(e)}"}

    assistantContent = """
    請幫我從申請表中提取用戶需要填寫的欄位，並以 JSON 格式輸出，確保欄位名稱與原始文件一致，格式為欄位名稱:欄位填寫處(預設是空白的，因為要給用戶填寫)，不要有階層式的。只需輸出 JSON 物件，不要包含任何額外的標籤或格式，例如「json」或「」這類的標記。範例如下：
    {"姓名":"","生日":""}
    """

    # 對話請求
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content([assistantContent, img])
        gemini_response = response.text

        # 嘗試解析為 JSON
        try:
            # 移除可能存在的 markdown 格式標記
            if gemini_response.startswith('```json') and gemini_response.endswith('```'):
                gemini_response = gemini_response[7:-3].strip()
            elif gemini_response.startswith('```') and gemini_response.endswith('```'):
                gemini_response = gemini_response[3:-3].strip()

            extracted_data = json.loads(gemini_response)

            # 確保 output 資料夾存在，如果不存在則創建
            output_folder = './output/'
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            # 儲存為 gemini.json
            file_path = os.path.join(output_folder, "0_gemini.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, ensure_ascii=False, indent=2)

            print(f"✅ Gemini 回傳內容已儲存至 {file_path}")

            return extracted_data

        except json.JSONDecodeError:
            print("❌ 解析 JSON 失敗，請檢查 Gemini 回傳的格式")
            print(f"Gemini 原始回傳內容: {gemini_response}")
            return {"error": "Gemini 回傳的內容格式不正確，無法解析 JSON", "raw_response": gemini_response}

    except Exception as e:
        print(f"❌ 執行 Gemini 處理發生錯誤: {str(e)}")
        return {"error": str(e)}


if __name__ == '__main__':
    # 測試圖片處理
    # 請確保在執行前，將 'GOOGLE_API_KEY' 設定在 .env 檔案中，並準備 '高雄大學社團.png' 圖片檔案
    # 範例圖片檔案路徑
    test_image_path = "高雄大學社團.png"
    print(f"正在使用圖片: {test_image_path} 進行測試...")
    result = extract_fields_from_image_gemini(test_image_path)
    print("\n--- 處理結果 ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))