# ============================================================================
# 权限管理 API（角色权限 + 用户级覆盖）
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.mysql import insert as mysql_insert
from loguru import logger

from app.database import get_db
from app.models.user import User
from app.models.permission import RoleComponentPermission, UserPermissionOverride
from app.services.redis import get_cached_permissions, cache_permissions
from app.schemas.permission import (
    PermissionUpdateRequest,
    UserPermissionsResponse,
    AdminPermissionsResponse,
    ComponentPermissionItem,
    UserInfo,
    UserPermissionsDetailResponse,
    UserPermissionDetail,
    UserPermissionOverrideRequest,
)
from app.middleware.auth import get_current_user, require_role

router = APIRouter(tags=["权限管理"])


# ============================================================================
# 用户自身权限查询（合并角色默认 + 个人覆盖）
# ============================================================================
@router.get("/api/user/permissions", response_model=UserPermissionsResponse)
async def get_user_permissions(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的最终组件权限（角色默认 + 个人覆盖，带 Redis 缓存）"""
    user_id = current_user["user_id"]

    # 尝试从 Redis 缓存获取
    cached = await get_cached_permissions(user_id)
    if cached:
        return UserPermissionsResponse(**cached)

    stmt = select(User).where(User.id == user_id, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    current_role = user.role.value

    # 1. 角色默认权限
    perm_stmt = select(RoleComponentPermission).where(RoleComponentPermission.role == current_role)
    perm_result = await db.execute(perm_stmt)
    role_perms = {p.component_key: p.allowed for p in perm_result.scalars().all()}

    # 2. 用户个人覆盖
    ovr_stmt = select(UserPermissionOverride).where(UserPermissionOverride.user_id == user.id)
    ovr_result = await db.execute(ovr_stmt)
    overrides = {}
    for ovr in ovr_result.scalars().all():
        overrides[ovr.component_key] = ovr.override_type

    # 3. 合并: (角色默认 OR grant) AND NOT deny
    all_keys = set(list(role_perms.keys()) + list(overrides.keys()))
    final_components = []
    for key in all_keys:
        role_allowed = role_perms.get(key, False)
        override = overrides.get(key)
        if override == "grant":
            effective = True
        elif override == "deny":
            effective = False
        else:
            effective = role_allowed
        if effective:
            final_components.append(key)

    result = UserPermissionsResponse(
        role=current_role,
        username=user.username,
        components=sorted(final_components),
        overrides=overrides,
    )

    # 写入 Redis 缓存（60 秒 TTL，权限变更时自然过期）
    await cache_permissions(user_id, result.model_dump())

    return result


# ============================================================================
# 管理员：角色默认权限管理
# ============================================================================
@router.get("/api/admin/permissions", response_model=AdminPermissionsResponse)
async def get_all_permissions(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """管理员查看所有角色的权限配置"""
    stmt = select(RoleComponentPermission).order_by(
        RoleComponentPermission.role, RoleComponentPermission.component_key
    )
    result = await db.execute(stmt)
    all_perms = result.scalars().all()

    grouped: dict[str, list[ComponentPermissionItem]] = {}
    for p in all_perms:
        item = ComponentPermissionItem(
            role=p.role, component_key=p.component_key, allowed=p.allowed, description=p.description
        )
        grouped.setdefault(p.role, []).append(item)

    return AdminPermissionsResponse(permissions=grouped)


@router.put("/api/admin/permissions")
async def update_permissions(
    body: PermissionUpdateRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """管理员批量更新角色默认权限"""
    try:
        for item in body.permissions:
            stmt = mysql_insert(RoleComponentPermission).values(
                role=item.role, component_key=item.component_key,
                allowed=item.allowed, description=item.description,
            )
            stmt = stmt.on_duplicate_key_update(
                allowed=stmt.inserted.allowed, description=stmt.inserted.description,
            )
            await db.execute(stmt)
        await db.commit()
        logger.info("管理员 {} 更新了 {} 项角色权限", current_user["username"], len(body.permissions))
        return {"message": "权限配置已更新", "count": len(body.permissions)}
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ============================================================================
# 管理员：用户级权限覆盖
# ============================================================================
@router.get("/api/admin/users", response_model=list[UserInfo])
async def list_users(
    role: str | None = Query(None, description="按角色筛选: admin/advanced/regular"),
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """获取所有活跃用户列表（可按角色筛选）"""
    stmt = select(User).where(User.is_active == True)
    if role:
        stmt = stmt.where(User.role == role)
    stmt = stmt.order_by(User.username)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [UserInfo(id=u.id, username=u.username, role=u.role.value, is_active=u.is_active) for u in users]


@router.get("/api/admin/users/{user_id}/permissions", response_model=UserPermissionsDetailResponse)
async def get_user_permission_detail(
    user_id: int,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """查看某用户的权限详情（角色默认 + 覆盖 + 最终结果）"""
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 角色默认
    perm_stmt = select(RoleComponentPermission).where(RoleComponentPermission.role == u.role.value)
    perm_result = await db.execute(perm_stmt)
    role_perms = {p.component_key: p for p in perm_result.scalars().all()}

    # 个人覆盖
    ovr_stmt = select(UserPermissionOverride).where(UserPermissionOverride.user_id == user_id)
    ovr_result = await db.execute(ovr_stmt)
    overrides = {o.component_key: o.override_type for o in ovr_result.scalars().all()}

    components = []
    all_keys = sorted(set(list(role_perms.keys()) + list(overrides.keys())))
    for key in all_keys:
        rp = role_perms.get(key)
        role_default = rp.allowed if rp else False
        ovr = overrides.get(key)
        if ovr == "grant":
            effective = True
        elif ovr == "deny":
            effective = False
        else:
            effective = role_default
        components.append(UserPermissionDetail(
            component_key=key,
            description=rp.description if rp else None,
            role_default=role_default,
            override=ovr,
            effective=effective,
        ))

    return UserPermissionsDetailResponse(
        user_id=u.id, username=u.username, role=u.role.value, components=components
    )


@router.put("/api/admin/users/{user_id}/permissions")
async def update_user_permissions(
    user_id: int,
    body: UserPermissionOverrideRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """更新某用户的权限覆盖"""
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")

    count = 0
    for item in body.overrides:
        component_key = item.get("component_key")
        override_type = item.get("override_type")

        if override_type is None:
            # 删除覆盖，恢复角色默认
            await db.execute(
                delete(UserPermissionOverride).where(
                    UserPermissionOverride.user_id == user_id,
                    UserPermissionOverride.component_key == component_key,
                )
            )
            count += 1
        elif override_type in ("grant", "deny"):
            stmt = mysql_insert(UserPermissionOverride).values(
                user_id=user_id, component_key=component_key, override_type=override_type,
            )
            stmt = stmt.on_duplicate_key_update(override_type=stmt.inserted.override_type)
            await db.execute(stmt)
            count += 1

    await db.commit()
    logger.info("管理员 {} 更新了用户 {} 的 {} 项权限覆盖", current_user["username"], u.username, count)
    return {"message": "用户权限已更新", "count": count}
