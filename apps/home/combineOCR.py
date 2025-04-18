import json
import os

# 容忍範圍（允許 OCR 座標有微小誤差）
HEIGHT_THRESHOLD = 5  # 允許的高度誤差（像素）


def find_fields_in_ocr(ocr_data, form_fields):
    """在 OCR 結果中找到對應的表單欄位，並返回格式化結果"""
    matched_fields = []

    for field in form_fields:
        field_words = field.replace(" ", "")  # 移除空格，確保匹配時不受影響
        bounding_box = None

        for line in ocr_data:
            line_text = line["LineText"].replace(" ", "")  # 也去掉 OCR 內容的空格
            if field_words in line_text:  # 如果整個欄位名稱在這一行的文字中
                bounding_box = merge_bounding_boxes(line)  # 取得合併的座標
                break  # 找到就跳出

        if bounding_box:
            x = bounding_box["x"]
            y = bounding_box["y"]
            w = bounding_box["width"]
            h = bounding_box["height"]
            matched_fields.append({
                "mode": "question",
                "name": field,
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "center_x": x + w / 2,
                "center_y": y + h / 2
            })

    return matched_fields


def merge_bounding_boxes(line):
    """直接使用 `Left, Top, Width, Height` 計算 bounding box"""
    if not line:
        return None

    return {
        "x": line["Left"],
        "y": line["Top"],
        "width": line["Width"],
        "height": line["Height"]
    }


def process_matched_fields(ocr_file="output/2_5_merged_paragraphs.json", gpt_file="output/0_gpt.json", output_file="output/3_matched_result.json"):
    # 確保 output 資料夾存在
    output_folder = os.path.dirname(output_file)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 讀取 OCR JSON
    with open(ocr_file, "r", encoding="utf-8") as f:
        ocr_data = json.load(f)

    # 讀取從 GPT 回傳的表單欄位
    with open(gpt_file, "r", encoding="utf-8") as f:
        form_fields = json.load(f)

    # 比對 OCR 內容，找出對應欄位
    matched_results = find_fields_in_ocr(ocr_data, form_fields)

    # 儲存結果
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(matched_results, f, ensure_ascii=False, indent=2)

    print(f"✅ 欄位匹配完成，結果已儲存至 {output_file}")
    return matched_results


# 只有當這個檔案被直接執行時才執行下面這行
if __name__ == "__main__":
    process_matched_fields()
