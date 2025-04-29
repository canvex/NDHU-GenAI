# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home import blueprint
from flask import render_template, request, redirect, url_for, jsonify, current_app


from werkzeug.utils import secure_filename
from apps import db
from apps.authentication.models import Files, Profile, OCRData, UsersProfile

from flask import flash  # 如果還沒有導入
from flask_login import login_required, current_user
from jinja2 import TemplateNotFound
import shutil
import os
import json
import apps.home.gpt as gpt  # GPT 模組
import apps.home.ocr as ocr  # OCR 模組
import apps.home.filterOCR as filterOCR
import apps.home.combineOCR as combineOCR
import apps.home.ai as detect_answer


@blueprint.route('/index')
#@login_required  # 確保使用者已登入
def index():
    return render_template('home/index.html', segment='index')


@blueprint.route('/doc_auto_select')
#@login_required  # 確保使用者已登入
def doc_auto_select():
    return render_template('home/doc_auto_select.html')

@blueprint.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        some_input = request.form.get('some_input')
        return redirect(url_for("home_blueprint.profile_edit"))
    
    # 查詢使用者的資料
    user_profile = UsersProfile.query.filter_by(user_id=current_user.id).first()
    
    # 如果資料不存在，可以選擇回傳空字典或處理未找到的情況
    if not user_profile:
        user_profile = {}

    # 解析生日 (假設是 'YYYY-MM-DD' 格式)
    if user_profile.birth_date:
        birth_year, birth_month, birth_day = user_profile.birth_date.split('-')
    else:
        birth_year, birth_month, birth_day = '', '', ''
    
    return render_template('home/profile.html', user_profile=user_profile,
                           birth_year=birth_year, birth_month=birth_month, birth_day=birth_day)



@blueprint.route('/profile_edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    user_id = current_user.id
    profile = db.session.query(UsersProfile).filter_by(user_id=user_id).first()

    if request.method == "POST":
        # 表單資料
        name = request.form.get("name")
        national_id = request.form.get("national_id")
        gender = request.form.get("gender")  # value 應該是 "男" 或 "女"
        birth_year = request.form.get("birth_year")
        birth_month = request.form.get("birth_month")
        birth_day = request.form.get("birth_day")
        birth_date = f"{birth_year}-{birth_month.zfill(2)}-{birth_day.zfill(2)}" if all([birth_year, birth_month, birth_day]) else None
        phone = request.form.get("phone")
        mobile = request.form.get("mobile")
        address = request.form.get("address")
        education = request.form.get("education")
        email = request.form.get("email")

        if not profile:
            profile = UsersProfile(user_id=user_id)

        # 更新資料
        profile.name = name
        profile.national_id = national_id
        profile.gender = gender
        profile.birth_date = birth_date
        profile.phone = phone
        profile.mobile = mobile
        profile.address = address
        profile.education = education
        profile.email = email
        db.session.add(profile)
        db.session.commit()
        return redirect(url_for("home_blueprint.profile"))

    return render_template("home/profile_edit.html", profile=profile)



@blueprint.route('/bounding_box')
def bounding():
    return render_template('home/bounding_box.html')


# 允許的文件類型
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@blueprint.route('/upload', methods=['POST'])
@login_required  # 確保使用者已登入
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        try:
            # 取得 UPLOAD_FOLDER 目錄
            upload_folder = current_app.config['UPLOAD_FOLDER']

            # 如果 uploads 目錄不存在，則創建
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            filename = file.filename
            file_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # 取得圖片資訊
            # img = Image.open(file_path)
            # width, height = img.size
            file_size = os.path.getsize(file_path)
            # shutil.rmtree("./output/")
            clear_output_folder()

            # 執行 GPT
            try:
                gpt_response = gpt.extract_fields_from_image(file_path)
            except Exception as e:
                return jsonify({'error': f'GPT 解析錯誤: {str(e)}'}), 500

            # 執行 OCR
            try:
                ocr_status = ocr.ocr_space_file(
                    file_path, output_json='output/1_ocr_result.json', language='cht')
            except Exception as e:
                return jsonify({'error': f'OCR 處理錯誤: {str(e)}'}), 500

            filterOCR.process_ocr_result()
            combineOCR.process_matched_fields()

            # # 呼叫 detect_answer 模組
            try:
                detect_answer.detect_answers(file_path)
            except Exception as e:
                return jsonify({'error': f'Roboflow 處理錯誤: {str(e)}'}), 500

            with open("output/3_matched_result.json", "r", encoding="utf-8") as f:
                content = json.load(f)

            response_data = {
                'filename': filename,
                # 'width': width,
                # 'height': height,
                'size_kb': round(file_size / 1024, 2),
                'gpt_response': gpt_response,
                'ocr_status': ocr_status,
                'ocr_data': content
            }

            return jsonify(response_data)

        except Exception as e:
            return jsonify({'error': f'上傳處理錯誤: {str(e)}'}), 500

    return jsonify({'error': 'Upload failed'}), 500


# 這段要保留
@blueprint.route('/doc_upload', methods=['GET', 'POST'])
@login_required  # 確保使用者已登入
def doc_upload():
    if request.method == 'POST':
        some_input = request.form.get('some_input')
        return redirect(url_for('home/blueprint.doc_download'))  # 确保正确的路由

    return render_template('home/doc_upload.html', segment='doc_upload')


# 文件上傳
@blueprint.route('/doc_select', methods=['POST'])
@login_required
def doc_select():
    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        user_id = None

    # === 基本檢查 ===
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    try:
        # === 檔案處理 ===
        file_data = file.read()
        max_size = 10 * 1024 * 1024
        if len(file_data) > max_size:
            return jsonify({'error': 'File too large'}), 400

        filename = secure_filename(file.filename)
        new_file = Files(
            file_name=file.filename,  # 直接使用原始檔案名稱
            file_type=filename.rsplit('.', 1)[1].lower(),
            file_size=len(file_data),
            file_data=file_data,
            user_id=user_id
        )
        db.session.add(new_file)
        db.session.commit()

        # === 儲存實體檔案 ===
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        file_path = os.path.join(upload_folder, filename)
        with open(file_path, "wb") as f:
            f.write(file_data)

        file_size = os.path.getsize(file_path)

        # === 處理流程 ===
        clear_output_folder()

        try:
            gpt_response = gpt.extract_fields_from_image(file_path)
        except Exception as e:
            return jsonify({'error': f'GPT 解析錯誤: {str(e)}'}), 500

        try:
            ocr_status = ocr.ocr_space_file(
                file_path, output_json='output/1_ocr_result.json', language='cht')
        except Exception as e:
            return jsonify({'error': f'OCR 處理錯誤: {str(e)}'}), 500

        filterOCR.process_ocr_result()
        combineOCR.process_matched_fields()

        try:
            detect_answer.detect_answers(file_path)
        except Exception as e:
            return jsonify({'error': f'Roboflow 處理錯誤: {str(e)}'}), 500

        with open("output/3_matched_result.json", "r", encoding="utf-8") as f:
            ocr_content = json.load(f)

        # === 儲存 OCR 資料 ===
        # 創建多條OCR記錄
        ocr_records = OCRData.create_from_ocr_content(
            file_id=new_file.id,
            ocr_content=ocr_content,
            user_id=user_id
        )
        db.session.add_all(ocr_records)
        db.session.commit()

        # 構建與 /upload 路由一致的響應格式
        response_data = {
            'filename': file.filename,  # 使用原始檔名
            'size_kb': round(file_size / 1024, 2),
            'gpt_response': gpt_response,
            'ocr_status': ocr_status,
            'ocr_data': ocr_content  # 保持與 /upload 相同的原始格式
        }

        return jsonify(response_data), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"文件處理錯誤: {str(e)}", exc_info=True)
        return jsonify({'error': f'伺服器錯誤: {str(e)}'}), 500


# 文件填寫
@blueprint.route('/doc_fill', methods=['GET', 'POST'])
def doc_fill():
    if request.method == 'POST':
        some_input = request.form.get('some_input')
        return redirect(url_for('home/blueprint.doc_download'))  # 确保正确的路由

    return render_template('home/doc_fill.html')

# 文件下載


@blueprint.route('/doc_download', methods=['GET', 'POST'])
def doc_download():
    if request.method == 'POST':
        some_input = request.form.get('some_input')  # 确保表单有这个字段
        if not some_input:
            return "Invalid input", 400  # 返回错误状态码
    return render_template('home/doc_download.html')


@blueprint.route('/<template>')
def route_template(template):

    try:

        if not template.endswith('.html'):
            template += '.html'

        # Detect the current page
        segment = get_segment(request)

        # Serve the file (if exists) from app/templates/home/FILE.html
        return render_template("home/" + template, segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except:
        return render_template('home/page-500.html'), 500


@blueprint.route('/api/profile', methods=['GET'])
@login_required  # 確保使用者已經登入
def get_profile():
    if current_user.is_authenticated:  # 檢查是否已登入
        # 查找當前用戶對應的 Profile
        profile = Profile.query.filter_by(user_id=current_user.id).first()
        if profile:
            user_profile = {
                'email': current_user.email,
                'name': profile.name,
                'department': profile.department,
                'student_id': profile.student_id,
                'phone': profile.phone,
                "personal_id": profile.national_id

            }
            return jsonify(user_profile)
        else:
            return jsonify({'error': 'Profile not found'}), 404
    else:
        return jsonify({'error': 'Unauthorized'}), 401


@blueprint.route('/api/userfiles', methods=['GET'])
@login_required  # 確保用戶必須登入才能訪問
def get_user_files():
    # 使用 current_user 來獲取目前登入的用戶
    user_id = current_user.id  # current_user.id 是 Flask-Login 提供的當前登入用戶的 ID

    # 查詢該用戶的所有檔案
    files = Files.query.filter_by(user_id=user_id).all()
    
    # 組織回傳的資料
    result = []
    for file in files:
        result.append({
            'id': file.id,
            'file_name': file.file_name,
            'file_type': file.file_type,
            'file_size': file.file_size,
            'upload_time': file.upload_time.isoformat() if file.upload_time else None
        })
    
    return jsonify(result)
# Helper - Extract current page name from request


def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None


def clear_output_folder():
    output_folder = "./output/"

    # 如果 output 目錄不存在，就創建它
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        open(os.path.join(output_folder, ".gitkeep"),
             "w").close()  # 確保 .gitkeep 存在
        return  # 剛創建，裡面沒有東西，不需要刪除

    # 遍歷 output 資料夾內的所有檔案與資料夾
    for filename in os.listdir(output_folder):
        file_path = os.path.join(output_folder, filename)
        try:
            if filename != ".gitkeep":  # 保留 .gitkeep
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # 刪除資料夾及其內容
        except Exception as e:
            print(f"❌ 無法刪除 {file_path}: {e}")
