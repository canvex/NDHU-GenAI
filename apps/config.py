import os, random, string

class Config(object):
    basedir = os.path.abspath(os.path.dirname(__file__))

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
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://ndhu:2025genai@152.70.110.2/ndhu_genai')


class ProductionConfig(Config):
    DEBUG = False
    # 部署到雲端（例如 AWS RDS, GCP, Azure）時使用的 MySQL 連線
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://ndhu:2025genai@152.70.110.2/ndhu_genai')

# 設定對應的 config_dict
config_dict = {
    'Debug': DebugConfig,
    'Production': ProductionConfig
}
