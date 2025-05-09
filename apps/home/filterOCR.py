import json
import os

Y_TOLERANCE = 10  # 上下容錯範圍
MAX_X_DISTANCE = 100  # 最大 x 軸距離

def is_same_line(word, line_words):
    for existing_word in line_words:
        y_diff = abs(word["Top"] - existing_word["Top"])
        if y_diff <= Y_TOLERANCE:
            x_diff = abs(word["Left"] - (existing_word["Left"] + existing_word["Width"]))
            if x_diff <= MAX_X_DISTANCE:
                return True
    return False


def merge_words_into_lines(words):
    lines = []

    for word in sorted(words, key=lambda w: w["Top"]):
        added = False
        for line in lines:
            if is_same_line(word, line):
                line.append(word)
                added = True
                break
        if not added:
            lines.append([word])

    # 合併每行文字並計算邊界框
    merged_lines = []
    for line_words in lines:
        sorted_words = sorted(line_words, key=lambda w: w["Left"])
        line_text = "".join([w["WordText"] for w in sorted_words])
        left = min(w["Left"] for w in sorted_words)
        top = min(w["Top"] for w in sorted_words)
        right = max(w["Left"] + w["Width"] for w in sorted_words)
        bottom = max(w["Top"] + w["Height"] for w in sorted_words)

        merged_lines.append({
            "LineText": line_text,
            "Left": left,
            "Top": top,
            "Width": right - left,
            "Height": bottom - top
        })

    return merged_lines


def extract_all_words_from_ocr(ocr_data):
    """從 OCR JSON 抽出所有 Words"""
    words = []
    for result in ocr_data.get("ParsedResults", []):
        for line in result.get("TextOverlay", {}).get("Lines", []):
            words.extend(line.get("Words", []))
    return words


def process(input_file="output/1_ocr_result.json", output_file="output/2_5_merged_paragraphs.json"):
    output_folder = os.path.dirname(output_file)
    os.makedirs(output_folder, exist_ok=True)

    with open(input_file, "r", encoding="utf-8") as f:
        ocr_data = json.load(f)

    all_words = extract_all_words_from_ocr(ocr_data)
    merged_lines = merge_words_into_lines(all_words)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged_lines, f, ensure_ascii=False, indent=2)

    print(f"✅ 合併完成，結果儲存至 {output_file}")
    return merged_lines


if __name__ == "__main__":
    process()
