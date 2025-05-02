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

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.LargeBinary, nullable=False)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
            if property == 'password':
                value = hash_pass(value)
            setattr(self, property, value)

    def __repr__(self):
        return str(self.username)

from sqlalchemy import event

class UsersProfile(db.Model):
    __tablename__ = 'users_profile'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id', ondelete='CASCADE'), nullable=False, unique=True)
    name = db.Column(db.String(64), nullable=True, default=None)  # 改為 default=None
    national_id = db.Column(db.String(10), nullable=True, default=None)
    gender = db.Column(db.String(1), nullable=True, default=None)
    birth_date = db.Column(db.String(10), nullable=True, default=None)
    phone = db.Column(db.String(15), nullable=True, default=None)
    mobile = db.Column(db.String(15), nullable=True, default=None)
    address = db.Column(db.String(255), nullable=True, default=None)
    education = db.Column(db.String(64), nullable=True, default=None)
    email = db.Column(db.String(128), nullable=True, default=None)

    def __repr__(self):
        return f"<UsersProfile user_id={self.user_id} name={self.name}>"

# --- 自動同步建立 users_profile ---
@event.listens_for(Users, 'after_insert')
def create_users_profile(mapper, connection, target):
    new_profile = {
        'user_id': target.id,
        'name': None,  # 全部欄位明確設為 None
        'national_id': None,
        'gender': None,
        'birth_date': None,
        'phone': None,
        'mobile': None,
        'address': None,
        'education': None,
        'email': None
    }
    connection.execute(
        UsersProfile.__table__.insert(),
        [new_profile]
    )


class Files(db.Model):
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_name = db.Column(db.String(255), nullable=False)  # 現在直接儲存原始檔案名稱
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id', ondelete='SET NULL'), nullable=True)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            setattr(self, property, value)
    
    def __repr__(self):
        return f'<File {self.file_name}>'
    
class Profile(db.Model):
    __tablename__ = 'profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False, unique=True)
    name = db.Column(db.String(64), nullable=True)
    department = db.Column(db.String(64), nullable=True)
    student_id = db.Column(db.String(64), nullable=True)
    national_id = db.Column(db.String(64), nullable=True)
    phone = db.Column(db.String(10), nullable=True)

    def __repr__(self):
        return f"<Profile user_id={self.user_id} name={self.name}>"

class OCRData(db.Model):
    __tablename__ = 'ocr_data'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id', ondelete='CASCADE'), nullable=False)
    ocr_data = db.Column(db.JSON)  # 可選的原始JSON數據
    
    # OCR 項目字段
    center_x = db.Column(db.Float)
    center_y = db.Column(db.Float)
    height = db.Column(db.Float)
    width = db.Column(db.Float)
    x = db.Column(db.Float)
    y = db.Column(db.Float)
    item_id = db.Column(db.String(20))  # 對應原始JSON中的id
    mode = db.Column(db.String(20))    # question/answer等類型
    item_name = db.Column(db.String(255))  # 項目名稱
    
    # 元數據
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 建立與Files表的關係
    file = db.relationship('Files', backref=db.backref('ocr_records', lazy=True))

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            setattr(self, property, value)

    @classmethod
    def create_from_ocr_content(cls, file_id, ocr_content, user_id=None):
        """從OCR內容創建多條記錄"""
        records = []
        if isinstance(ocr_content, list):
            for item in ocr_content:
                record = cls(
                    file_id=file_id,
                    user_id=user_id,
                    # 結構化字段
                    center_x=item.get('center_x'),
                    center_y=item.get('center_y'),
                    height=item.get('height'),
                    width=item.get('width'),
                    x=item.get('x'),
                    y=item.get('y'),
                    item_id=item.get('id'),
                    mode=item.get('mode'),
                    item_name=item.get('name'),
                    # 可選保留原始JSON
                    ocr_data=item
                )
                records.append(record)
        return records

    def to_dict(self):
        """轉換為字典格式"""
        return {
            'file_id': self.file_id,
            'height': self.height,
            'width': self.width,
            'x': self.x,
            'y': self.y,
            'id': self.item_id,
            'mode': self.mode,
            'name': self.item_name
        }

    def __repr__(self):
        return f'<OCRData (File ID: {self.file_id}, Item ID: {self.item_id})>'



@login_manager.user_loader
def user_loader(id):
    return Users.query.filter_by(id=id).first()

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = Users.query.filter_by(username=username).first()
    return user if user else None