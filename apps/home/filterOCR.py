import json
import os

# 容忍範圍
TOP_THRESHOLD = 10  # 允許的行高誤差（像素）
GAP_THRESHOLD = 200  # 同一行內，詞與詞之間的最大間隔（像素）


def merge_text_lines(ocr_data):
    """整理段落文字，合併同一行，並保留正確的座標名稱"""
    lines = []

    # 依照 Top 值排序，確保從上到下排列
    sorted_words = sorted(
        [word for line in ocr_data for word in line["Words"]],
        key=lambda w: (w["Top"], w["Left"])  # 先按照 Top，再按照 Left 排序
    )

    temp_line = []
    last_top = None
    last_left = None

    for word in sorted_words:
        if last_top is None or abs(word["Top"] - last_top) <= TOP_THRESHOLD:
            # 如果這不是第一個詞，且與上一個詞的距離過大，則視為新的一行
            if last_left is not None and (word["Left"] - last_left) > GAP_THRESHOLD:
                lines.append(create_line_entry(temp_line))  # 儲存上一行
                temp_line = []  # 開啟新行

            temp_line.append(word)
        else:
            # 遇到新的一行，儲存上一行的內容
            lines.append(create_line_entry(temp_line))
            temp_line = [word]  # 開啟新行

        last_top = word["Top"]
        last_left = word["Left"] + word["Width"]  # 記錄上一個詞的 Right 位置

    if temp_line:
        lines.append(create_line_entry(temp_line))  # 儲存最後一行

    return lines


def create_line_entry(words):
    """合併多個詞，計算整行的 bounding box，並修改欄位名稱"""
    if not words:
        return None

    # **修正**：先按照 `Left` 排序，確保文字順序正確
    sorted_words = sorted(words, key=lambda w: w["Left"])

    line_text = "".join([word["WordText"] for word in sorted_words])

    left = min(word["Left"] for word in sorted_words)
    top = min(word["Top"] for word in sorted_words)
    right = max(word["Left"] + word["Width"] for word in sorted_words)
    bottom = max(word["Top"] + word["Height"] for word in sorted_words)

    return {
        "LineText": line_text,
        "Left": left,  # `x` 改成 `Left`
        "Top": top,    # `y` 改成 `Top`
        "Width": right - left,   # `width` 改成 `Width`
        "Height": bottom - top   # `height` 改成 `Height`
    }


def process_merged_paragraphs(input_file="output/2_filtered_result.json", output_file="output/2_5_merged_paragraphs.json"):
    """讀取 OCR JSON，處理文字合併，並儲存結果"""
    # 確保 output 資料夾存在
    output_folder = os.path.dirname(output_file)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    with open(input_file, "r", encoding="utf-8") as f:
        ocr_data = json.load(f)

    # 處理文字合併
    merged_paragraphs = merge_text_lines(ocr_data)

    # 儲存結果
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged_paragraphs, f, ensure_ascii=False, indent=2)

    print(f"✅ 2.段落整理完成，結果已儲存至 {output_file}")
    return merged_paragraphs


def process_ocr_result(input_file="output/1_ocr_result.json", output_file="output/2_filtered_result.json"):
    # 確保 output 資料夾存在
    output_folder = os.path.dirname(output_file)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 讀取 JSON 檔案
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 過濾出需要的資訊
    filtered_data = []
    for result in data.get("ParsedResults", []):
        for line in result.get("TextOverlay", {}).get("Lines", []):
            filtered_data.append({
                "LineText": line["LineText"],
                "Words": line["Words"]
            })

    # 儲存成新的 JSON 檔案
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 1.過濾完成，結果已儲存至 {output_file}")
    return process_merged_paragraphs()


# 只有當這個檔案被直接執行時才執行下面這行
if __name__ == "__main__":
    process_ocr_result()
    # process_merged_paragraphs()
