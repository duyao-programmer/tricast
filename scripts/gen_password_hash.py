"""
预生成 bcrypt 密码哈希，供 init.sql 使用。

用法: python scripts/gen_password_hash.py admin123 adv123 reg123
"""
import sys
import bcrypt


def main():
    if len(sys.argv) < 2:
        print("用法: python gen_password_hash.py <password1> [password2] ...")
        print("示例: python gen_password_hash.py admin123 adv123 reg123")
        sys.exit(1)

    for pwd in sys.argv[1:]:
        pwd_bytes = pwd.encode("utf-8")
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")
        print(f"密码: {pwd}")
        print(f"哈希: {hashed}")
        print()


if __name__ == "__main__":
    main()
