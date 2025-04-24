# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from datetime import datetime
from flask_login import UserMixin
from apps import db, login_manager
from apps.authentication.util import hash_pass

class Users(db.Model, UserMixin):

    __tablename__ = 'Users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 明確指定 autoincrement
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.LargeBinary, nullable=False)  # 確保密碼欄位不能為 NULL

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack its value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]

            if property == 'password':
                value = hash_pass(value)  # we need bytes here (not plain str)

            setattr(self, property, value)

    def __repr__(self):
        return str(self.username)


class Files(db.Model):
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id', ondelete='SET NULL'), nullable=True)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)  # 新增上传时间
    original_name = db.Column(db.String(255))  # 保留原始文件名
    
    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            setattr(self, property, value)
    
    def __repr__(self):
        return f'<File {self.file_name}>'


class OCRData(db.Model):
    __tablename__ = 'ocr_data'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)  # 不含副檔名
    original_name = db.Column(db.String(255))  # 原始完整檔名
    
    # OCR 數據拆分後的獨立欄位
    center_x = db.Column(db.Float, nullable=False)
    center_y = db.Column(db.Float, nullable=False)
    height = db.Column(db.Float, nullable=False)
    ocr_id = db.Column(db.String(50), nullable=False)  # 原 json 中的 id 欄位
    mode = db.Column(db.String(20), nullable=False)  # question/answer
    name = db.Column(db.String(255), nullable=False)  # 可能是數字或文字
    width = db.Column(db.Float, nullable=False)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id', ondelete='SET NULL'), nullable=True)

    # 建立與 Files 表的關係
    file = db.relationship('Files', backref=db.backref('ocr_records', lazy=True))

    def __init__(self, **kwargs):
        # 處理基礎檔案資訊
        for property in ['file_id', 'filename', 'original_name', 'user_id']:
            if property in kwargs:
                if property == 'filename' and '.' in kwargs[property]:
                    setattr(self, property, kwargs[property].split('.')[0])
                else:
                    setattr(self, property, kwargs[property])
        
        # 處理 OCR 數據
        if 'ocr_data' in kwargs:
            ocr_item = kwargs['ocr_data']  # 假設傳入的是單個 OCR 項目
            self.center_x = ocr_item['center_x']
            self.center_y = ocr_item['center_y']
            self.height = ocr_item['height']
            self.ocr_id = ocr_item['id']
            self.mode = ocr_item['mode']
            self.name = str(ocr_item['name'])  # 確保轉為字串
            self.width = ocr_item['width']
            self.x = ocr_item['x']
            self.y = ocr_item['y']

    def __repr__(self):
        return f'<OCRData {self.ocr_id} (File ID: {self.file_id})>'


@login_manager.user_loader
def user_loader(id):
    return Users.query.filter_by(id=id).first()

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = Users.query.filter_by(username=username).first()
    return user if user else None