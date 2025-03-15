# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home import blueprint
from flask import render_template, request, redirect, url_for

from flask_login import login_required
from jinja2 import TemplateNotFound



@blueprint.route('/index')
def index():

    return render_template('home/index.html', segment='index')

#文件上傳
@blueprint.route('/doc_upload', methods=['GET', 'POST'])
def doc_upload():
    if request.method == 'POST':
        some_input = request.form.get('some_input')
        return redirect(url_for('home/blueprint.doc_select'))  # 确保正确的路由

    return render_template('home/doc_upload.html')

#文件選取
@blueprint.route('/doc_select', methods=['GET', 'POST'])
def doc_select():
    if request.method == 'POST':
        some_input = request.form.get('some_input')
        return redirect(url_for('home/blueprint.doc_fill'))  # 确保正确的路由

    return render_template('home/doc_select.html')


#文件填寫
@blueprint.route('/doc_fill', methods=['GET', 'POST'])
def doc_fill():
    if request.method == 'POST':
        some_input = request.form.get('some_input')
        return redirect(url_for('home/blueprint.doc_download'))  # 确保正确的路由

    return render_template('home/doc_fill.html')

#文件下載
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
