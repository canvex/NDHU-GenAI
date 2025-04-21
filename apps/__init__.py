# 修改 apps/__init__.py，確保與 MySQL 相容
import os
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module

# 初始化 MySQL 資料庫連線
db = SQLAlchemy()
login_manager = LoginManager()

def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)

def register_blueprints(app):
    for module_name in ('authentication', 'home'):
        module = import_module('apps.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

def create_app(config_class='apps.config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ✅ 加入這段：設定 SQLAlchemy engine options 以處理 MySQL 斷線問題
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,    # 自動檢查連線是否有效
        'pool_recycle': 1800      # 每 30 分鐘回收一次連線
    }

    register_extensions(app)
    register_blueprints(app)

    with app.app_context():
        db.create_all()  # 確保 MySQL 資料庫表格被創建

    return app
