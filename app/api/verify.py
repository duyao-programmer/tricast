# ============================================================================
# Nginx auth_request 专用验证端点（internal，外部不可达）
# ============================================================================
from fastapi import APIRouter, Request, HTTPException, status
from jose import JWTError, ExpiredSignatureError
from loguru import logger

from app.services.auth import decode_access_token
from app.services.redis import is_token_blacklisted

router = APIRouter(prefix="/api/auth", tags=["认证验证"])


@router.get("/verify")
async def verify_token(request: Request):
    """
    Nginx auth_request 专用端点。
    从 Cookie（优先）或 Authorization header 提取 JWT，
    验证签名和过期时间，成功返回 200 + 用户信息响应头。

    此端点被 nginx.conf 中 `location = /api/auth/verify { internal; }` 保护，
    外部请求会被 Nginx 直接拒绝（404）。
    """
    # 优先从 Cookie 读取
    token = request.cookies.get("access_token")

    # 降级：兼容 Authorization header
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )

    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期",
        )
    except JWTError as e:
        logger.debug("JWT 验证失败: {}", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效",
        )

    # 检查 JWT 黑名单
    jti = payload.get("jti", "")
    if jti and await is_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已失效",
        )

    # 返回用户信息到响应头（Nginx 通过 auth_request_set 传递给后续 proxy）
    response_headers = {
        "X-User-Id": str(payload["user_id"]),
        "X-User-Role": payload["role"],
        "X-User-Name": payload["username"],
    }
    from fastapi.responses import Response
    return Response(status_code=200, headers=response_headers)
