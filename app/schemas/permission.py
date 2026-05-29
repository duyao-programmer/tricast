# ============================================================================
# 权限管理 Pydantic Schema
# ============================================================================
from pydantic import BaseModel, Field


class ComponentPermissionItem(BaseModel):
    """单个组件权限配置"""
    role: str = Field(..., description="角色名")
    component_key: str = Field(..., description="组件唯一标识")
    allowed: bool = Field(..., description="是否允许")
    description: str | None = Field(None, description="说明")


class PermissionUpdateRequest(BaseModel):
    """管理员批量更新权限的请求体"""
    permissions: list[ComponentPermissionItem] = Field(..., description="权限配置列表")


class UserPermissionsResponse(BaseModel):
    """当前用户的组件权限列表（含覆盖信息）"""
    role: str = Field(..., description="当前角色")
    username: str = Field(..., description="用户名")
    components: list[str] = Field(..., description="允许访问的组件列表")
    overrides: dict[str, str] = Field(default={}, description="用户的覆盖记录: {component_key: 'grant'|'deny'}")


class UserInfo(BaseModel):
    """用户简要信息（供管理员选择）"""
    id: int
    username: str
    role: str
    is_active: bool


class UserPermissionDetail(BaseModel):
    """某用户对某一组件的权限详情"""
    component_key: str
    description: str | None = None
    role_default: bool  # 角色默认是否允许
    override: str | None = None  # 'grant' / 'deny' / None
    effective: bool  # 最终是否允许


class UserPermissionsDetailResponse(BaseModel):
    """用户权限详情（管理员查看）"""
    user_id: int
    username: str
    role: str
    components: list[UserPermissionDetail]


class UserPermissionOverrideRequest(BaseModel):
    """更新单个用户的权限覆盖"""
    overrides: list[dict[str, object]] = Field(..., description="[{component_key: str, override_type: 'grant'|'deny'|None}, ...]")


class AdminPermissionsResponse(BaseModel):
    """管理员视角：按角色分组的完整权限配置"""
    permissions: dict[str, list[ComponentPermissionItem]] = Field(
        ..., description="按角色分组的权限，如 {'admin': [...], 'advanced': [...], 'regular': [...]}"
    )
