# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home import blueprint
from flask import render_template, request
from flask_login import login_required
from jinja2 import TemplateNotFound


@blueprint.route('/index')
def index():

    return render_template('doc_upload.html', segment='index')


@blueprint.route('/doc_select', methods=['GET', 'POST'])
def doc_select():
    if request.method == 'POST':
        some_input = request.form.get('some_input')  # 確保表單有這個欄位
        if not some_input:
            return "Invalid input", 400  # 返回錯誤狀態碼
    return render_template('doc_select.html')


@blueprint.route('/doc_fill', methods=['GET', 'POST'])
def doc_fill():
    if request.method == 'POST':
        some_input = request.form.get('some_input')  # 確保表單有這個欄位
        if not some_input:
            return "Invalid input", 400  # 返回錯誤狀態碼
    return render_template('doc_fill.html')


@blueprint.route('/doc_download', methods=['GET', 'POST'])
def doc_download():
    if request.method == 'POST':
        some_input = request.form.get('some_input')  # 確保表單有這個欄位
        if not some_input:
            return "Invalid input", 400  # 返回錯誤狀態碼
    return render_template('doc_download.html')


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
