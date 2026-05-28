# ============================================================================
# JWT 认证依赖注入 + 角色校验
# ============================================================================
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from app.services.auth import decode_access_token
from loguru import logger

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """
    从 Authorization: Bearer <token> 中提取并验证 JWT，
    返回用户信息字典 {user_id, username, role}
    """
    token = credentials.credentials
    try:
        user_info = decode_access_token(token)
        return user_info
    except JWTError as e:
        logger.warning("JWT 验证失败: {}", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
        )


def require_role(*allowed_roles: str):
    """
    角色校验依赖工厂

    用法:
        @router.get("/admin-only")
        async def admin_endpoint(user=Depends(require_role("admin"))):
            ...

    Args:
        allowed_roles: 允许的角色列表
    """

    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {'/'.join(allowed_roles)} 权限",
            )
        return user

    return role_checker
