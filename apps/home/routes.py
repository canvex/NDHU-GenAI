# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home import blueprint
from flask import render_template, request, redirect, url_for, jsonify, current_app

from flask import flash  # 如果還沒有導入
from flask_login import login_required, current_user
from flask_login import login_required
from jinja2 import TemplateNotFound
import shutil
import os
import apps.home.gpt as gpt  # GPT 模組
import apps.home.ocr as ocr  # OCR 模組
import apps.home.filterOCR as filterOCR
import apps.home.combineOCR as combineOCR


@blueprint.route('/index')
def index():

    return render_template('home/index.html', segment='index')


@blueprint.route('/bounding_box')
def bounding():
    return render_template('home/bounding_box.html')


@blueprint.route('/upload', methods=['POST'])
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
            finalocr = combineOCR.process_matched_fields()

            response_data = {
                'filename': filename,
                # 'width': width,
                # 'height': height,
                'size_kb': round(file_size / 1024, 2),
                'gpt_response': gpt_response,
                'ocr_status': ocr_status,
                'ocr_data': finalocr
            }

            return jsonify(response_data)

        except Exception as e:
            return jsonify({'error': f'上傳處理錯誤: {str(e)}'}), 500

    return jsonify({'error': 'Upload failed'}), 500

# 文件上傳
@blueprint.route('/doc_upload', methods=['GET', 'POST'])
@login_required  # 確保使用者已登入
def doc_upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('沒有選擇檔案', 'danger')
            return redirect(url_for('home_blueprint.doc_upload'))
        
        file = request.files['file']
        
        if file.filename == '':
            flash('沒有選擇檔案', 'danger')
            return redirect(url_for('home_blueprint.doc_upload'))
        
        if file:
            from werkzeug.utils import secure_filename
            from flask_login import current_user
            from apps import db
            from apps.authentication.models import Files
            
            # 處理檔案安全名稱
            filename = secure_filename(file.filename)
            # 讀取檔案內容
            file_data = file.read()
            # 取得檔案大小
            file_size = len(file_data)
            # 取得檔案類型
            file_type = file.content_type
            
            
            # 建立新的檔案記錄
            new_file = Files(
                file_name=filename,
                file_type=file_type,
                file_size=file_size,
                file_data=file_data,
                user_id=current_user.id if current_user.is_authenticated else None
            )
            
            try:
                # 儲存到資料庫
                db.session.add(new_file)
                db.session.commit()
                flash('檔案上傳成功', 'success')
                return redirect(url_for('home_blueprint.doc_select'))
            except Exception as e:
                db.session.rollback()
                flash(f'檔案上傳失敗: {str(e)}', 'danger')
                return redirect(url_for('home_blueprint.doc_upload'))

    return render_template('home/doc_upload.html', segment='doc_upload')

# 文件選取


@blueprint.route('/doc_select', methods=['GET', 'POST'])
def doc_select():
    if request.method == 'POST':
        some_input = request.form.get('some_input')
        return redirect(url_for('home/blueprint.doc_fill'))  # 确保正确的路由

    return render_template('home/doc_select.html')


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
