# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home import blueprint
from flask import render_template, request, redirect, url_for, jsonify, current_app


from werkzeug.utils import secure_filename
from apps import db
from apps.authentication.models import Files, OCRData, UsersProfile

from flask import flash  # 如果還沒有導入
from flask import abort
from flask_login import login_required, current_user
from jinja2 import TemplateNotFound
import shutil
import os
import json
import base64
import apps.home.gemini_vision as gemini_vision  # Gemini 模組
import apps.home.ocr as ocr  # OCR 模組
import apps.home.filterOCR as filterOCR
import apps.home.combineOCR as combineOCR
import apps.home.ai as detect_answer


@blueprint.route("/index")
#@login_required  # 確保使用者已登入
def index():
    return render_template("home/index.html", segment="index")


@blueprint.route("/doc_auto_select")
#@login_required  # 確保使用者已登入
def doc_auto_select():
    return render_template("home/doc_auto_select.html", mode="first_upload", file_id=None)

@blueprint.route("/test")
#@login_required  # 確保使用者已登入
def test():
    return render_template("home/test.html")

@blueprint.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    
    # 查詢使用者的資料
    user_profile = UsersProfile.query.filter_by(user_id=current_user.id).first()
    
    # 如果資料不存在，可以選擇回傳空字典或處理未找到的情況
    if not user_profile:
        user_profile = {}

    # 解析生日 (假設是 \'YYYY-MM-DD\' 格式)
    if user_profile.birth_date:
        birth_year, birth_month, birth_day = user_profile.birth_date.split("-")
    else:
        birth_year, birth_month, birth_day = "", "", ""
    
    return render_template("home/profile.html", user_profile=user_profile,
                           birth_year=birth_year, birth_month=birth_month, birth_day=birth_day)



@blueprint.route("/profile_edit", methods=["GET", "POST"])
@login_required
def profile_edit():
    user_id = current_user.id
    profile = db.session.query(UsersProfile).filter_by(user_id=user_id).first_or_404()

    if request.method == "POST":
        # 定義空值過濾函數 (加強版)
        def clean_input(value):
            # 明確處理 None、空字符串、純空白字符
            if value is None or (isinstance(value, str) and not value.strip()):
                return None
            return str(value).strip()

        # 處理所有表單欄位 (包含可能被清空的欄位)
        form_data = {
            "name": clean_input(request.form.get("name")),
            "national_id": clean_input(request.form.get("national_id")),
            "gender": clean_input(request.form.get("gender")),
            "phone": clean_input(request.form.get("phone")),
            "mobile": clean_input(request.form.get("mobile")),
            "address": clean_input(request.form.get("address")),
            "education": clean_input(request.form.get("education")),
            "email": clean_input(request.form.get("email"))
        }

        # 特殊處理生日 (組合年月日)
        birth_year = clean_input(request.form.get("birth_year"))
        birth_month = clean_input(request.form.get("birth_month"))
        birth_day = clean_input(request.form.get("birth_day"))
        form_data["birth_date"] = (
            f"{birth_year}-{birth_month.zfill(2)}-{birth_day.zfill(2)}"
            if all([birth_year, birth_month, birth_day])
            else None
        )

        # 關鍵修改點：強制更新所有欄位，包括被清空的值
        for field, value in form_data.items():
            setattr(profile, field, value)  # 移除了 value is not None 的檢查

        db.session.commit()
        flash("個人資料已更新", "success")  # 新增成功提示
        return redirect(url_for("home_blueprint.profile"))

    # GET 請求處理 (確保 None 不會渲染為字符串)
    return render_template(
        "home/profile_edit.html",
        profile=profile,
        # 確保前端模板收到正確的空值處理
        null_to_empty=lambda x: x if x is not None else ""
    )


@blueprint.route("/bounding_box")
def bounding():
    return render_template("home/bounding_box.html", mode="first_upload", file_id=None)

# 允許的文件類型
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    if not filename:
        return False
    
    # 使用 os.path.splitext 更安全的獲取擴展名
    _, ext = os.path.splitext(filename)
    
    # 檢查擴展名是否存在且合法
    if not ext:
        return False
    
    # 去掉點號並轉為小寫比較
    return ext[1:].lower() in ALLOWED_EXTENSIONS


@blueprint.route("/upload", methods=["POST"])
@login_required  # 確保使用者已登入
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file:
        try:
            # 取得 UPLOAD_FOLDER 目錄
            upload_folder = current_app.config["UPLOAD_FOLDER"]

            # 如果 uploads 目錄不存在，則創建
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            filename = file.filename
            file_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)

            # 取得圖片資訊
            # img = Image.open(file_path)
            # width, height = img.size
            file_size = os.path.getsize(file_path)
            # shutil.rmtree("./output/")
            clear_output_folder()

            # 執行 Gemini
            try:
                gpt_response = gemini_vision.extract_fields_from_image_gemini(file_path)
            except Exception as e:
                return jsonify({"error": f"Gemini 解析錯誤: {str(e)}"}), 500

            # 執行 OCR
            try:
                ocr_status = ocr.ocr_space_file(
                    file_path, output_json="output/1_ocr_result.json", language="cht")
            except Exception as e:
                return jsonify({"error": f"OCR 處理錯誤: {str(e)}"}), 500

            filterOCR.process()
            combineOCR.process_matched_fields()

            # # 呼叫 detect_answer 模組
            try:
                detect_answer.detect_answers(file_path)
            except Exception as e:
                return jsonify({"error": f"Roboflow 處理錯誤: {str(e)}"}), 500

            with open("output/3_matched_result.json", "r", encoding="utf-8") as f:
                ocr_content = json.load(f)

            # === 儲存 OCR 資料 ===
            ocr_records = OCRData.create_from_ocr_content(
                file_id=new_file.id,
                ocr_content=ocr_content,
                user_id=user_id
            )
            
            current_app.logger.info(f"準備儲存 {len(ocr_records)} 筆 OCR 記錄到資料庫，file_id: {new_file.id}")
            if not ocr_records:
                current_app.logger.warning("ocr_records 為空，沒有資料被儲存。")

            db.session.add_all(ocr_records)
            db.session.commit()
            current_app.logger.info(f"OCR 記錄已成功提交到資料庫，file_id: {new_file.id}")

            # 獲取當前登入使用者的個人資料
            user_profile_data = {}
            if current_user.is_authenticated:
                user_profile = UsersProfile.query.filter_by(user_id=current_user.id).first()
                if user_profile:
                    user_profile_data = {
                        "name": user_profile.name,
                        "gender": user_profile.gender,
                        "birth_date": user_profile.birth_date,
                        "national_id": user_profile.national_id, # 注意：這裡會解密
                        "phone": user_profile.phone, # 注意：這裡會解密
                        "mobile": user_profile.mobile, # 注意：這裡會解密
                        "address": user_profile.address, # 注意：這裡會解密
                        "education": user_profile.education, # 注意：這裡會解密
                        "email": user_profile.email # 注意：這裡會解密
                    }

            response_data = {
                "filename": filename,
                # "width": width,
                # "height": height,
                "size_kb": round(file_size / 1024, 2),
                "gpt_response": gpt_response,
                "ocr_status": ocr_status,
                "ocr_data": ocr_content,
                "user_profile": user_profile_data # 新增使用者個人資料
            }

            return jsonify(response_data)

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"文件上傳或處理失敗: {str(e)}", exc_info=True)
            return jsonify({"error": f"文件上傳或處理失敗: {str(e)}"}), 500

    return jsonify({"error": "Upload failed"}), 500


# 這段要保留
@blueprint.route("/doc_upload", methods=["GET", "POST"])
@login_required  # 確保使用者已登入
def doc_upload():
    if request.method == "POST":
        some_input = request.form.get("some_input")
        return redirect(url_for("home_blueprint.doc_download"))  # 确保正确的路由

    return render_template("home/doc_upload.html", segment="doc_upload")


# 文件上傳與儲存
@blueprint.route("/doc_select", methods=["POST"])
@login_required
def doc_select():
    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        user_id = None

     # === 區分 JSON 資料更新請求 ===
    if request.content_type == "application/json":
        try:
            data = request.get_json()
            ocr_content = data.get("ocr_data")
            file_id = data.get("file_id")
            
            if not ocr_content or not file_id:
                return jsonify({"error": "缺少必要參數: ocr_data 或 file_id"}), 400
                
            # 檢查檔案是否存在
            file_record = Files.query.get(file_id)
            if not file_record:
                return jsonify({"error": "指定的檔案不存在"}), 404
                
            # 刪除舊的 OCR 資料
            OCRData.query.filter_by(file_id=file_id).delete()
            
            # 創建新的 OCR 記錄
            ocr_records = OCRData.create_from_ocr_content(
                file_id=file_id,
                ocr_content=ocr_content,
                user_id=user_id
            )
            db.session.add_all(ocr_records)
            db.session.commit()
            
            return jsonify({"message": " 檔案資料更新成功"}), 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"OCR 資料更新錯誤: {str(e)}", exc_info=True)
            return jsonify({"error": f"伺服器錯誤: {str(e)}"}), 500
        

    # === 基本檢查 ===
    if "file" not in request.files:
        return jsonify({"error": "請求中缺少檔案部分"}), 400

    file = request.files["file"]  # 只有在檔案上傳時才會賦值
    if file.filename == "":
        return jsonify({"error": "未選擇檔案"}), 400

    # 檢查文件類型
    if not allowed_file(file.filename):
        return jsonify({"error": "不允許的文件類型，僅支持png、jpg、jpeg格式"}), 400

    # 檢查文件名是否全中文（不包含英文或數字）
    def is_all_chinese(filename):
        # 移除文件擴展名
        name_part = os.path.splitext(filename)[0]
        # 檢查每個字符是否都是中文字符
        for char in name_part:
            if not '\u4e00' <= char <= '\u9fff':
             return False
        return True

    if is_all_chinese(os.path.splitext(file.filename)[0]):
        return jsonify({"error": "檔名不能為全中文，請包含英文或數字"}), 400

    try:
        # === 檔案處理 ===
        file_data = file.read()
        max_size = 10 * 1024 * 1024
        if len(file_data) > max_size:
            return jsonify({"error": "File too large"}), 400

        filename = secure_filename(file.filename)
        new_file = Files(
            file_name=file.filename,  # 直接使用原始檔案名稱
            file_type=filename.rsplit(".", 1)[1].lower(),
            file_size=len(file_data),
            file_data=file_data,
            user_id=user_id
        )
        db.session.add(new_file)
        db.session.commit()

        # === 儲存實體檔案 ===
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        file_path = os.path.join(upload_folder, filename)
        with open(file_path, "wb") as f:
            f.write(file_data)

        file_size = os.path.getsize(file_path)

        # === 處理流程 ===
        clear_output_folder()

        try:
            gpt_response = gemini_vision.extract_fields_from_image_gemini(file_path)
        except Exception as e:
            return jsonify({"error": f"Gemini 解析錯誤: {str(e)}"}), 500

        try:
            ocr_status = ocr.ocr_space_file(
                file_path, output_json="output/1_ocr_result.json", language="cht")
        except Exception as e:
            return jsonify({"error": f"OCR 處理錯誤: {str(e)}"}), 500

        filterOCR.process()
        combineOCR.process_matched_fields()

        try:
            detect_answer.detect_answers(file_path)
        except Exception as e:
            return jsonify({"error": f"Roboflow 處理錯誤: {str(e)}"}), 500

        with open("output/3_matched_result.json", "r", encoding="utf-8") as f:
            ocr_content = json.load(f)

        # === 儲存 OCR 資料 ===
        ocr_records = OCRData.create_from_ocr_content(
            file_id=new_file.id,
            ocr_content=ocr_content,
            user_id=user_id
        )
        
        current_app.logger.info(f"準備儲存 {len(ocr_records)} 筆 OCR 記錄到資料庫，file_id: {new_file.id}")
        if not ocr_records:
            current_app.logger.warning("ocr_records 為空，沒有資料被儲存。")

        db.session.add_all(ocr_records)
        db.session.commit()
        current_app.logger.info(f"OCR 記錄已成功提交到資料庫，file_id: {new_file.id}")

        # 獲取當前登入使用者的個人資料
        user_profile_data = {}
        if current_user.is_authenticated:
            user_profile = UsersProfile.query.filter_by(user_id=current_user.id).first()
            if user_profile:
                user_profile_data = {
                    "name": user_profile.name,
                    "gender": user_profile.gender,
                    "birth_date": user_profile.birth_date,
                    "national_id": user_profile.national_id, # 注意：這裡會解密
                    "phone": user_profile.phone, # 注意：這裡會解密
                    "mobile": user_profile.mobile, # 注意：這裡會解密
                    "address": user_profile.address, # 注意：這裡會解密
                    "education": user_profile.education, # 注意：這裡會解密
                    "email": user_profile.email # 注意：這裡會解密
                }

        # 將檔案 ID 和使用者個人資料傳遞給前端
        return jsonify({
            "msg": "文件上傳成功",
            "file_id": new_file.id,
            "file_name": new_file.file_name,
            "ocr_data": ocr_content,
            "gpt_response": gpt_response,
            "user_profile": user_profile_data # 新增使用者個人資料
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"文件上傳或處理失敗: {str(e)}", exc_info=True)
        return jsonify({"error": f"文件上傳或處理失敗: {str(e)}"}), 500

    return jsonify({"error": "Upload failed"}), 500


@blueprint.route("/api/profile", methods=["GET"])
@login_required
def api_profile():
    """
    提供目前登入使用者的個人資料，供前端自動填表使用。
    """
    profile = UsersProfile.query.filter_by(user_id=current_user.id).first()

    if not profile:
        return jsonify({"error": "使用者資料不存在"}), 404

    # 日期轉換成字串格式
    birth_date_str = ""
    try:
        if profile.birth_date:
            if isinstance(profile.birth_date, str):
                birth_date_str = profile.birth_date
            else:
                birth_date_str = profile.birth_date.strftime("%Y-%m-%d")
    except Exception:
        birth_date_str = ""

    # 安全取值（不存在欄位不會報錯）
    def safe_get(obj, field):
        return getattr(obj, field, "") or ""

    return jsonify({
        "姓名": safe_get(profile, "name"),
        "性別": safe_get(profile, "gender"),
        "生日": birth_date_str,
        "電話": safe_get(profile, "phone"),
        "行動電話": safe_get(profile, "mobile"),
        "地址": safe_get(profile, "address"),
        "電子郵件": safe_get(profile, "email"),
        "教育程度": safe_get(profile, "education"),
        "身分證字號": safe_get(profile, "national_id"),
    })



@blueprint.route("/doc_download/<int:file_id>")
@login_required
def doc_download(file_id):
    file_record = Files.query.get(file_id)
    if not file_record:
        abort(404)

    # 從資料庫中讀取 OCRData
    ocr_data_records = OCRData.query.filter_by(file_id=file_id).all()
    ocr_content = [
        {
            "field_name": record.field_name,
            "field_value": record.field_value,
            "bounding_box": json.loads(record.bounding_box) if record.bounding_box else None,
            "confidence": record.confidence,
            "page_num": record.page_num
        }
        for record in ocr_data_records
    ]

    # 讀取 gpt_response (假設它儲存在 output/0_gemini.json 中)
    gpt_response = {}
    gpt_response_path = os.path.join(current_app.config["BASE_DIR"], "output", "0_gemini.json")
    if os.path.exists(gpt_response_path):
        with open(gpt_response_path, "r", encoding="utf-8") as f:
            gpt_response = json.load(f)

    # 讀取 matched_result (假設它儲存在 output/3_matched_result.json 中)
    matched_result = {}
    matched_result_path = os.path.join(current_app.config["BASE_DIR"], "output", "3_matched_result.json")
    if os.path.exists(matched_result_path):
        with open(matched_result_path, "r", encoding="utf-8") as f:
            matched_result = json.load(f)

    # 將資料傳遞給模板
    return render_template(
        "home/doc_download.html",
        file_record=file_record,
        ocr_content=json.dumps(ocr_content, ensure_ascii=False, indent=2),
        gpt_response=json.dumps(gpt_response, ensure_ascii=False, indent=2),
        matched_result=json.dumps(matched_result, ensure_ascii=False, indent=2)
    )

@blueprint.route("/api/userfiles", methods=["GET"])
@login_required
def api_userfiles():
    """
    回傳目前登入使用者上傳過的所有文件列表。
    """
    files = Files.query.filter_by(user_id=current_user.id).all()

    return jsonify([
        {
            "id": f.id,
            "filename": f.file_name,
            "filetype": f.file_type,
            "filesize": f.file_size
        } for f in files
    ])


@blueprint.route("/doc_modify/<int:file_id>", methods=["GET", "POST"])
@login_required
def doc_modify(file_id):
    file_record = Files.query.get(file_id)
    if not file_record:
        abort(404)

    if request.method == "POST":
        try:
            modified_ocr_data = request.get_json()
            
            # 清除舊的 OCRData 記錄
            OCRData.query.filter_by(file_id=file_id).delete()
            db.session.commit()

            # 儲存新的 OCRData 記錄
            for item in modified_ocr_data:
                new_ocr_data = OCRData(
                    file_id=file_id,
                    field_name=item["field_name"],
                    field_value=item["field_value"],
                    bounding_box=json.dumps(item["bounding_box"]) if item["bounding_box"] else None,
                    confidence=item["confidence"],
                    page_num=item["page_num"]
                )
                db.session.add(new_ocr_data)
            db.session.commit()

            return jsonify({"message": "OCR Data updated successfully"}), 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating OCR data: {str(e)}")
            return jsonify({"error": "Failed to update OCR data"}), 500

    # GET 請求，顯示修改頁面
    ocr_data_records = OCRData.query.filter_by(file_id=file_id).all()
    ocr_content = [
        {
            "field_name": record.field_name,
            "field_value": record.field_value,
            "bounding_box": json.loads(record.bounding_box) if record.bounding_box else None,
            "confidence": record.confidence,
            "page_num": record.page_num
        }
        for record in ocr_data_records
    ]

    gpt_response = {}
    gpt_response_path = os.path.join(current_app.config["BASE_DIR"], "output", "0_gemini.json")
    if os.path.exists(gpt_response_path):
        with open(gpt_response_path, "r", encoding="utf-8") as f:
            gpt_response = json.load(f)

    return render_template(
        "home/doc_modify.html",
        file_record=file_record,
        ocr_content=json.dumps(ocr_content, ensure_ascii=False, indent=2),
        gpt_response=json.dumps(gpt_response, ensure_ascii=False, indent=2)
    )


@blueprint.route("/doc_delete/<int:file_id>", methods=["POST"])
@login_required
def doc_delete(file_id):
    file_record = Files.query.get(file_id)
    if not file_record:
        flash("文件未找到", "error")
        return redirect(url_for("home_blueprint.doc_auto_select"))

    try:
        # 刪除相關的 OCRData 記錄
        OCRData.query.filter_by(file_id=file_id).delete()
        db.session.delete(file_record)
        db.session.commit()
        flash("文件及其相關資料已成功刪除", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"刪除文件失敗: {str(e)}", "error")

    return redirect(url_for("home_blueprint.doc_auto_select"))

def clear_output_folder():
    output_folder = "./output/"
    if os.path.exists(output_folder):
        for filename in os.listdir(output_folder):
            file_path = os.path.join(output_folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")


@blueprint.route("/<template>")
#@login_required
def route_template(template):

    try:

        if not template.endswith(".html"):
            template += ".html"

        # Detect the current page
        segment = get_segment(request)

        # Serve the file (if exists)
        return render_template("home/" + template, segment=segment)

    except TemplateNotFound:
        return render_template("home/page-404.html"), 404

    except:
        return render_template("home/page-500.html"), 500

# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split("/")[-1]

        if segment == "":
            segment = "index"

        return segment

    except:
        return None