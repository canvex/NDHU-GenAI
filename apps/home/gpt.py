import os
import json
import base64
import threading
from openai import OpenAI
import requests
from io import BytesIO
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def extract_fields_from_image(image_path):

    # 從環境變數讀取 API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("❌ 環境變數 OPENAI_API_KEY 未設定")

    client = OpenAI(api_key=api_key)

    assistantContent = """
    請幫我從申請表中提取用戶需要填寫的欄位，並以 JSON 格式輸出，確保欄位名稱與原始文件一致，格式為欄位名稱:欄位填寫處(預設是空白的，因為要給用戶填寫)，不要有階層式的。只需輸出 JSON 物件，不要包含任何額外的標籤或格式，例如「json」或「」這類的標記。範例如下：
    {"姓名":"","生日":""}
    """

    # Getting the Base64 string
    base64_image = encode_image(image_path)

    # 對話請求
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            # {"role": "assistant", "content": assistantContent},
            {"role": "user", "content": [
                {
                    "type": "text",
                    "text": assistantContent
                },
                {
                    "type": "image_url",
                    # "image_url": {"url": "https://i.imgur.com/dCs8p3k.png"}  # 圖片連結
                    # base64
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                }
            ]}
        ]
    )

    gpt_response = completion.choices[0].message.content

    # 嘗試解析為 JSON
    try:
        extracted_data = json.loads(gpt_response)

        # 確保 output 資料夾存在，如果不存在則創建
        output_folder = './output/'
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # 儲存為 gpt.json
        file_path = os.path.join(output_folder, "0_gpt.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=2)

        print(f"✅ GPT 回傳內容已儲存至 {file_path}")

        return extracted_data

    except json.JSONDecodeError:
        print("❌ 解析 JSON 失敗，請檢查 GPT 回傳的格式")
        return {"error": "GPT 回傳的內容格式不正確，無法解析 JSON"}

    except Exception as e:
        print(f"❌ 執行 GPT 處理發生錯誤: {str(e)}")
        return {"error": str(e)}


if __name__ == '__main__':
    # 測試圖片處理
    # result = process_image("高雄大學社團.png")
    result = encode_image("高雄大學社團.png")
    print(result)
