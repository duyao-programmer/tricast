# ============================================================================
# 注册、登录接口（含限流+锁定重置）
# ============================================================================
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
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
from app.services.auth import hash_password, verify_password, create_access_token

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
    body: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录。5次失败锁定15分钟，成功登录重置计数。
    """
    # 获取客户端 IP
    client_ip = request.client.host if request.client else "unknown"

    # 查找用户
    stmt = select(User).where(User.username == body.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 检查账户是否被锁定
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = (user.locked_until - datetime.utcnow()).seconds // 60
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"账户已被锁定，请 {remaining} 分钟后重试",
        )

    # 检查账户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    # 验证密码
    if not verify_password(body.password, user.password_hash):
        # 密码错误：记录失败日志 + 增加失败计数（需要显式提交，防止 get_db 回滚）
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

    # 密码正确：重置失败计数和锁定状态
    user.failed_login_attempts = 0
    user.locked_until = None

    # 生成 JWT
    token, expires_in = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
    )

    logger.info("用户 {}（{}）登录成功", user.username, user.role.value)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        username=user.username,
        role=user.role.value,
    )
