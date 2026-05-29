# ============================================================================
# RoleComponentPermission + UserPermissionOverride ORM 模型
# ============================================================================
from sqlalchemy import Boolean, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.user import Base


class RoleComponentPermission(Base):
    __tablename__ = "role_component_permissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, comment="角色名")
    component_key: Mapped[str] = mapped_column(String(100), nullable=False, comment="组件唯一标识")
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否允许")
    description: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="说明")


class UserPermissionOverride(Base):
    __tablename__ = "user_permission_overrides"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    component_key: Mapped[str] = mapped_column(String(100), nullable=False, comment="组件标识")
    override_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="grant=额外授权, deny=额外禁止")
