import os, random, string
from dotenv import load_dotenv

load_dotenv()

class Config(object):
    basedir = os.path.abspath(os.path.dirname(__file__))

    # 直接指定 UPLOAD_FOLDER，不依賴 .env 檔案
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')  # 或者根據需要修改路徑
    
    # Assets Management
    ASSETS_ROOT = os.getenv('ASSETS_ROOT', '/static/assets')

    # Set up the App SECRET_KEY
    SECRET_KEY = os.getenv('SECRET_KEY', None)
    if not SECRET_KEY:
        SECRET_KEY = ''.join(random.choice(string.ascii_lowercase) for i in range(32))

    # 資料庫通用設定
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DebugConfig(Config):
    DEBUG = True
    # 本地開發時使用 MySQL，請確保你的 MySQL 伺服器允許連線
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')  # 從環境變數讀取


class ProductionConfig(Config):
    DEBUG = False
    # 部署到雲端（例如 AWS RDS, GCP, Azure）時使用的 MySQL 連線
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')  # 從環境變數讀取

# 設定對應的 config_dict
config_dict = {
    'Debug': DebugConfig,
    'Production': ProductionConfig
}
