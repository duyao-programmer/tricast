# ============================================================================
# 注册、登录接口（含限流+锁定重置）
# ============================================================================
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from loguru import logger

from app.database import get_db
from app.models.user import User, UserRole, FailedLoginLog
from app.schemas.user import (
    UserRegisterRequest, UserLoginRequest,
    TokenResponse, UserResponse,
)
from app.services.auth import hash_password, verify_password, create_access_token, decode_access_token
from app.services.redis import blacklist_token

router = APIRouter(prefix="/api/auth", tags=["认证"])

limiter = Limiter(key_func=get_remote_address)

# ============================================================================
# 登录锁定参数
# ============================================================================
MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 15


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户注册，强制角色为 regular。
    请求体中的 role 字段（如有）会被忽略。
    """
    # 检查用户名是否已存在
    stmt = select(User).where(User.username == body.username)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在",
        )

    # 创建用户，强制 role=regular
    new_user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=UserRole.regular,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    logger.info("新用户注册: {} (role=regular)", body.username)

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        role=new_user.role.value,
        is_active=new_user.is_active,
        created_at=new_user.created_at.isoformat() if new_user.created_at else None,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    body: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录。JWT 通过 HttpOnly Cookie 下发，5次失败锁定15分钟。
    """
    client_ip = request.client.host if request.client else "unknown"

    stmt = select(User).where(User.username == body.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = (user.locked_until - datetime.utcnow()).seconds // 60
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"账户已被锁定，请 {remaining} 分钟后重试",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    if not verify_password(body.password, user.password_hash):
        fail_log = FailedLoginLog(
            username=body.username,
            ip_address=client_ip,
        )
        db.add(fail_log)

        user.failed_login_attempts += 1

        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCK_DURATION_MINUTES)
            logger.warning("用户 {} 登录失败 {} 次，锁定 {} 分钟", body.username, MAX_FAILED_ATTEMPTS, LOCK_DURATION_MINUTES)

        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    user.failed_login_attempts = 0
    user.locked_until = None

    token, expires_in = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
    )

    # JWT 存入 HttpOnly Cookie（浏览器自动携带，JS 无法读取，防御 XSS）
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=expires_in,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )

    logger.info("用户 {}（{}）登录成功", user.username, user.role.value)

    return TokenResponse(
        token_type="bearer",
        expires_in=expires_in,
        username=user.username,
        role=user.role.value,
    )


@router.post("/logout")
async def logout(request: Request, response: Response):
    """登出：清除 Cookie + 将 JWT 加入 Redis 黑名单"""
    # 提取当前 token 的 jti 并加入黑名单
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = decode_access_token(token)
            jti = payload.get("jti", "")
            if jti:
                # TTL = JWT 剩余过期时间（取整）
                import time
                remaining = max(1, int(payload.get("exp", time.time() + 3600) - time.time()))
                await blacklist_token(jti, remaining)
                logger.info("Token {} 已加入黑名单 (TTL {}s)", jti[:8], remaining)
        except Exception as e:
            logger.warning("黑名单写入失败: {}", e)

    response.set_cookie(
        key="access_token",
        value="",
        max_age=0,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return {"message": "已登出"}


# ============================================================================
# 密码修改请求 Schema
# ============================================================================
from pydantic import BaseModel, Field

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)


@router.post("/change-password")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """修改当前用户密码"""
    # 从 Cookie 提取当前用户
    from app.middleware.auth import _extract_token
    from app.services.auth import decode_access_token
    token = _extract_token(request, None)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="令牌无效")

    stmt = select(User).where(User.id == payload["user_id"])
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    # 验证旧密码
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")

    # 简单密码强度检查
    if not any(c.isupper() for c in body.new_password):
        raise HTTPException(status_code=400, detail="新密码需至少包含一个大写字母")
    if not any(c.islower() for c in body.new_password):
        raise HTTPException(status_code=400, detail="新密码需至少包含一个小写字母")
    if not any(c.isdigit() for c in body.new_password):
        raise HTTPException(status_code=400, detail="新密码需至少包含一个数字")

    user.password_hash = hash_password(body.new_password)
    await db.flush()
    logger.info("用户 {} 修改了密码", user.username)
    return {"message": "密码修改成功"}
