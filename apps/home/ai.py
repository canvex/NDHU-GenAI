import os
import json
import requests
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 從環境變數讀取 API Key
api_key = os.getenv("ROBOFLOW_API_KEY")
if not api_key:
    raise ValueError("❌ 環境變數 ROBOFLOW_API_KEY 未設定")

# Roboflow Model 設定
MODEL_ID = "my-first-project-ksnki/6"
API_URL = f"https://detect.roboflow.com/{MODEL_ID}?api_key={api_key}"


def detect_answers(image_path: str, output_json: str = 'output/3_matched_result.json'):
    """
    偵測圖片中的 answer 區塊，結果存入 JSON 檔案。
    :param image_path: 圖片檔案路徑
    :param output_json: 要寫入的 JSON 檔案名稱
    """
    try:
        with open(image_path, "rb") as img_file:
            res = requests.post(
                API_URL,
                files={"file": img_file}
            )
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[❌] Roboflow API 呼叫失敗: {e}")
        return

    try:
        result_json = res.json()
        predictions = result_json.get("predictions", [])
    except Exception as e:
        print(f"[❌] 回傳結果解析失敗: {e}")
        return

    filtered_results = []
    answer_idx = 0  # ✅ 只針對 answer 類別累加

    for pred in predictions:
        if pred["class"] != "answer":
            continue

        filtered_results.append({
            "id": f"a{answer_idx}",
            "mode": "answer",
            "name": "", # 目前留空，answer_idx
            "x": pred["x"] - pred["width"] / 2,
            "y": pred["y"] - pred["height"] / 2,
            "width": pred["width"],
            "height": pred["height"],
            "center_x": pred["x"],
            "center_y": pred["y"]
        })
        answer_idx += 1  # ✅ 手動增加

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
    detect_answers("apps/uploads/yourpic.jpg")
