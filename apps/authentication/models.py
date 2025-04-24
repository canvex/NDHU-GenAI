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
    ocr_data = db.Column(db.JSON, nullable=False)  # 保留原始JSON數據
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id', ondelete='SET NULL'), nullable=True)
    ocr_status = db.Column(db.String(20))  # 新增狀態欄位
    size_kb = db.Column(db.Float)  # 新增文件大小欄位
    success = db.Column(db.Boolean)  # 新增處理成功標記

    # 建立與 Files 表的關係
    file = db.relationship('Files', backref=db.backref('ocr_records', lazy=True))
    # 新增與OCRItem的一對多關係
    items = db.relationship('OCRItem', backref='ocr_data', lazy=True, cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if property == 'filename' and '.' in value:
                value = value.split('.')[0]  # 自動移除副檔名
            setattr(self, property, value)
        
        # 自動處理items關聯
        if 'ocr_data' in kwargs and kwargs['ocr_data']:
            self.process_ocr_items(kwargs['ocr_data'])

    def process_ocr_items(self, ocr_json):
        """將JSON數據解析為OCRItem對象"""
        for item in ocr_json:
            ocr_item = OCRItem(
                center_x=item.get('center_x'),
                center_y=item.get('center_y'),
                height=item.get('height'),
                width=item.get('width'),
                x=item.get('x'),
                y=item.get('y'),
                item_id=item.get('id'),
                mode=item.get('mode'),
                name=item.get('name'),
                ocr_data_id=self.id,
                user_id=self.user_id
            )
            self.items.append(ocr_item)

    def __repr__(self):
        return f'<OCRData {self.filename} (File ID: {self.file_id})>'


class OCRItem(db.Model):
    __tablename__ = 'ocr_items'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ocr_data_id = db.Column(db.Integer, db.ForeignKey('ocr_data.id', ondelete='CASCADE'), nullable=False)
    
    # 結構化字段
    center_x = db.Column(db.Float)
    center_y = db.Column(db.Float)
    height = db.Column(db.Float)
    width = db.Column(db.Float)
    x = db.Column(db.Float)
    y = db.Column(db.Float)
    item_id = db.Column(db.String(20))  # 對應原始JSON中的id
    mode = db.Column(db.String(20))  # question/answer等類型
    name = db.Column(db.String(255))  # 項目名稱
    
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id', ondelete='SET NULL'), nullable=True)
    
    # 時間戳記
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<OCRItem {self.item_id} (Data ID: {self.ocr_data_id})>'


@login_manager.user_loader
def user_loader(id):
    return Users.query.filter_by(id=id).first()

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = Users.query.filter_by(username=username).first()
    return user if user else None