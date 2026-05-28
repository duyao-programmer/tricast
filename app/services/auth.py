# ============================================================================
# JWT 生成/验证 + bcrypt 密码哈希服务
# ============================================================================
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import bcrypt
from app.config import settings
from loguru import logger


def hash_password(password: str) -> str:
    """使用 bcrypt 生成密码哈希"""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed: str) -> bool:
    """验证密码与 bcrypt 哈希是否匹配"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: int, username: str, role: str) -> tuple[str, int]:
    """
    创建 JWT 访问令牌

    Returns:
        (token, expires_in_seconds)
    """
    expire_minutes = settings.jwt_expire_minutes
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expire_minutes)

    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    expires_in = expire_minutes * 60

    return token, expires_in


def decode_access_token(token: str) -> dict:
    """
    解码并验证 JWT 令牌

    Returns:
        dict: 包含 user_id, username, role 的字典

    Raises:
        JWTError: 令牌无效或已过期
    """
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

    return {
        "user_id": int(payload["sub"]),
        "username": payload["username"],
        "role": payload["role"],
    }
