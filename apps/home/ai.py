from dotenv import load_dotenv
from inference_sdk.http.errors import HTTPCallErrorError
from inference_sdk import InferenceHTTPClient
import json
import os

# 載入環境變數
load_dotenv()

# 從環境變數讀取 API Key
api_key = os.getenv("ROBOFLOW_API_KEY")
if not api_key:
    raise ValueError("❌ 環境變數 ROBOFLOW_API_KEY 未設定")

# 初始化 InferenceHTTPClient，只需初始化一次
CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=api_key
)


def detect_answers(image_path: str, output_json: str = 'output/3_matched_result.json'):
    """
    偵測圖片中的 answer 區塊，結果存入 JSON 檔案。

    :param image_path: 圖片檔案路徑
    :param output_json: 要寫入的 JSON 檔案名稱
    """
    try:
        res = CLIENT.infer(image_path, model_id="my-first-project-ksnki/5")
    except HTTPCallErrorError as e:
        print(f"[❌] Roboflow API 呼叫失敗: {e.description}")
        print(f"狀態碼: {e.status_code}, 訊息: {e.api_message}")
        return  # 發生錯誤就不要繼續處理了

    filtered_results = [
        {
            "id": f"a{idx}",  # 新增 id 欄位，以 a 開頭
            "mode": "answer",
            "name": idx + 1,
            "x": pred["x"] - pred["width"] / 2,
            "y": pred["y"] - pred["height"] / 2,
            "width": pred["width"],
            "height": pred["height"],
            "center_x": pred["x"],
            "center_y": pred["y"]
        }
        for idx, pred in enumerate(res["predictions"])
        if pred["class"] == "answer"
    ]
    # print(filtered_results)

    # 讀取現有 JSON 資料
    try:
        with open(output_json, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    except FileNotFoundError:
        existing_data = []

    # 加入新結果
    existing_data.extend(filtered_results)

    # 寫回檔案
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 成功寫入 {len(filtered_results)} 筆資料到 {output_json}")


if __name__ == "__main__":
    detect_answers(
        "apps/uploads/yourpic.jpg")
