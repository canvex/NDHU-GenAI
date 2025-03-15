from util import hash_pass, verify_pass

test_password = "your_password"
hashed_pwd = hash_pass(test_password)
print("Hashed Password:", hashed_pwd)

if verify_pass(test_password, hashed_pwd):
    print("✅ 密碼驗證成功")
else:
    print("❌ 密碼驗證失敗")
