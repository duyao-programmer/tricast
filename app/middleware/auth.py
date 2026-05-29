# ============================================================================
# JWT 认证依赖注入 + 角色校验
# 优先从 HttpOnly Cookie 读取 JWT，降级兼容 Authorization header
# ============================================================================
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, ExpiredSignatureError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db
from app.models.user import User
from app.services.auth import decode_access_token
from app.services.redis import (
    is_token_blacklisted, get_cached_user_role, cache_user_role,
)

security_scheme = HTTPBearer(auto_error=False)


def _extract_token(request: Request, credentials: HTTPAuthorizationCredentials | None) -> str | None:
    """从 Cookie 或 Authorization header 提取 JWT"""
    # 优先从 Cookie 读取（浏览器自动携带）
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    # 降级：兼容 Authorization: Bearer <token>
    if credentials:
        return credentials.credentials

    return None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    从 Cookie（优先）或 Authorization header 提取 JWT，
    解码获取 user_id 后查询数据库获取最新角色。
    用户被禁用、删除后即时生效，无需重新登录。
    """
    token = _extract_token(request, credentials)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )

    # 解码 JWT（验证签名 + 过期时间）
    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期，请重新登录",
        )
    except JWTError as e:
        logger.warning("JWT 验证失败: {}", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
        )

    user_id = payload["user_id"]

    # JWT 黑名单检查（登出后即时失效）
    jti = payload.get("jti", "")
    if jti and await is_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已失效，请重新登录",
        )

    # Redis 缓存：先尝试从缓存获取用户角色
    cached = await get_cached_user_role(user_id)
    if cached:
        return cached

    # 缓存未命中：查询数据库
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    user_data = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role.value,
    }

    # 写入缓存（30 秒 TTL）
    await cache_user_role(user_id, user_data)

    return user_data


def require_role(*allowed_roles: str):
    """
    角色校验依赖工厂

    用法:
        @router.get("/admin-only")
        async def admin_endpoint(user=Depends(require_role("admin"))):
            ...
    """

    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {'/'.join(allowed_roles)} 权限",
            )
        return user

    return role_checker
