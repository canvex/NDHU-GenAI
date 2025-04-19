# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home import blueprint
from flask import render_template, request, redirect, url_for, jsonify, current_app


from werkzeug.utils import secure_filename
from apps import db
from apps.authentication.models import Files




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
@login_required  # 確保使用者已登入
def index():

    return render_template('home/index.html', segment='index')


@blueprint.route('/bounding_box')
def bounding():
    return render_template('home/bounding_box.html')

# 允許的文件類型
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'gif'}

@blueprint.route('/upload', methods=['POST'])
@login_required  # 確保使用者已登入
def upload_image():
    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        user_id = None

    # === 前段：基本檢查 ===
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    try:
        # === 檔案資料與 DB 儲存 ===
        file_data = file.read()
        max_size = 10 * 1024 * 1024
        if len(file_data) > max_size:
            return jsonify({'error': 'File too large'}), 400

        filename = secure_filename(file.filename)
        new_file = Files(
            file_name=filename,
            original_name=file.filename,
            file_type=filename.rsplit('.', 1)[1].lower(),
            file_size=len(file_data),
            file_data=file_data,
            user_id=user_id
        )
        db.session.add(new_file)
        db.session.commit()

        # === 儲存實體檔案至 uploads 資料夾 ===
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        file_path = os.path.join(upload_folder, filename)
        with open(file_path, "wb") as f:
            f.write(file_data)

        file_size = os.path.getsize(file_path)

        # === 處理流程：GPT + OCR + Roboflow ===
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
            content = json.load(f)

        return jsonify({
            'success': True,
            'message': 'File uploaded and processed successfully',
            'file_id': new_file.id,
            'filename': filename,
            'size_kb': round(file_size / 1024, 2),
            'gpt_response': gpt_response,
            'ocr_status': ocr_status,
            'ocr_data': content
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'伺服器錯誤: {str(e)}'}), 500


# 文件上傳
@blueprint.route('/doc_upload', methods=['GET', 'POST'])
@login_required  # 確保使用者已登入
def doc_upload():
    if request.method == 'POST':
        some_input = request.form.get('some_input')
        return redirect(url_for('home/blueprint.doc_download'))  # 确保正确的路由
    
    return render_template('home/doc_upload.html', segment='doc_upload')


# 文件選取



@blueprint.route('/doc_select', methods=['POST'])
def doc_select():
    # 检查用户是否登录（如果需要）
    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        user_id = None
    
    # 检查请求是否包含文件
    if 'file' not in request.files:
        current_app.logger.error('No file part in request')
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    # 检查是否选择了文件
    if file.filename == '':
        current_app.logger.error('Empty filename')
        return jsonify({'error': 'No file selected'}), 400
    
    # 检查文件类型
    if not allowed_file(file.filename):
        current_app.logger.error(f'Invalid file type: {file.filename}')
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        # 读取文件内容
        file_data = file.read()
        
        # 检查文件大小（例如限制10MB）
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_data) > max_size:
            return jsonify({'error': 'File size exceeds 10MB limit'}), 400
        
        # 安全处理文件名
        filename = secure_filename(file.filename)
        
        # 创建文件记录
        new_file = Files(
            file_name=filename,
            original_name=file.filename,  # 保存原始文件名
            file_type=filename.rsplit('.', 1)[1].lower(),
            file_size=len(file_data),
            file_data=file_data,
            user_id=user_id
        )
        
        db.session.add(new_file)
        db.session.commit()
        
        current_app.logger.info(f'File uploaded successfully: {filename}')
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'file_id': new_file.id,
            'file_name': new_file.file_name
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Upload failed: {str(e)}', exc_info=True)
        return jsonify({'error': 'Server error during upload'}), 500
    
    print('🔥 收到請求 method:', request.method)  # ← 第一層：有沒有進來 POST

    if request.method == 'POST':
        print('🧾 request.files:', request.files)     # ← 看看有沒有檔案
        print('📦 request.form:', request.form)       # ← 有沒有表單欄位
        print('🗂 request.data:', request.data)        # ← 是否為空

        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file part'})

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'})

        # ✅ 寫入磁碟（簡單測試）
        filepath = os.path.join('uploads', file.filename)
        file.save(filepath)
        print(f'✅ 檔案儲存成功: {filepath}')

        # ✅ 寫入資料庫（你可以先註解掉資料庫部分測試有沒有寫入磁碟）
        # new_file = File(filename=file.filename, ...)
        # db.session.add(new_file)
        # db.session.commit()

        return jsonify({'success': True, 'file_name': file.filename})

    # GET 方法處理
    return render_template('home/doc_select.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
