import os
import requests
import json
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()


def ocr_space_file(filename, output_json="output.json", overlay=True, language='cht'):
    """ 使用 OCR.space API 處理本地圖片，並將結果存為 JSON
    :param filename: 圖片檔案路徑
    :param output_json: 儲存 JSON 的路徑
    :param overlay: 是否啟用 Overlay
    :param api_key: OCR.space API Key
    :param language: OCR 語言
    :return: OCR JSON 結果
    """
    api_key = os.getenv('OCR_SPACE_API_KEY')
    if not api_key:
        raise ValueError("❌ 環境變數 OCR_SPACE_API_KEY 未設定")
    payload = {
        'isOverlayRequired': overlay,
        'apikey': api_key,
        'isTable': "true",
        'language': language,
        'OCREngine': 2,
        'scale': "true"
    }

    try:
        with open(filename, 'rb') as f:
            r = requests.post('https://api.ocr.space/parse/image',
                              files={os.path.basename(filename): f},
                              data=payload,
                              timeout=10)  # 設定 15 秒的 timeout

        result = r.json()

        # 檢查是否有錯誤
        if not result.get('IsErroredOnProcessing', False):
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"✅ OCR JSON 結果已儲存至 {output_json}")
            return "OK"
        else:
            print("❌ OCR 處理錯誤:", result.get('ErrorMessage', '未知錯誤'))
            return "Not OK"

    except requests.Timeout:
        print("❌ 請求超時，可能是 OCR.space API 無回應或網路問題")
        return "Timeout Error"
    except requests.RequestException as e:
        print(f"❌ 其他請求錯誤: {e}")
        return "Request Error"


if __name__ == '__main__':
    # 使用範例：
    test_file = ocr_space_file(
        filename='高雄大學社團.png', output_json='1_ocr_result.json', language='cht')

# 測試遠端圖片（如果需要使用 URL）
# test_url = ocr_space_url(url='http://i.imgur.com/31d5L5y.jpg', output_json='ocr_result.json', language='cht')
