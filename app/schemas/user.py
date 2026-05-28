# ============================================================================
# 用户注册/登录请求响应 Pydantic Schema
# ============================================================================
from pydantic import BaseModel, Field, field_validator


class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """校验用户名仅含字母、数字、下划线"""
        if not v.replace("_", "").isalnum():
            raise ValueError("用户名只能包含字母、数字和下划线")
        return v.strip()


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=1, max_length=100, description="密码")


class TokenResponse(BaseModel):
    """登录成功返回的 JWT 令牌"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒
    username: str
    role: str


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    role: str
    is_active: bool
    created_at: str | None = None

    model_config = {"from_attributes": True}
