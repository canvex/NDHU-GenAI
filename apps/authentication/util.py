import bcrypt

def hash_pass(password):
    """使用 bcrypt 來哈希密碼"""
    salt = bcrypt.gensalt()  # 產生隨機 salt
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)  # 生成哈希
    return hashed  # 回傳 bytes

def verify_pass(provided_password, stored_password):
    """驗證密碼是否匹配"""
    if isinstance(provided_password, str):
        provided_password = provided_password.encode('utf-8')
    if isinstance(stored_password, str):
        stored_password = stored_password.encode('utf-8')
    return bcrypt.checkpw(provided_password, stored_password)
