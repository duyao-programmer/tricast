# ============================================================================
# 仪表盘统计 API
# ============================================================================
from datetime import date, datetime
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.message import Message
from app.models.user import User
from app.models.subscription import MessageTagLink, MessageTag
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


@router.get("/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """仪表盘统计数据"""
    today = date.today()

    # 总消息数
    total_msgs_result = await db.execute(select(func.count(Message.id)))
    total_messages = total_msgs_result.scalar()

    # 今日发布数
    today_msgs_result = await db.execute(
        select(func.count(Message.id)).where(func.date(Message.published_at) == today)
    )
    today_messages = today_msgs_result.scalar()

    # 各角色用户数
    role_result = await db.execute(
        select(User.role, func.count(User.id)).where(User.is_active == True).group_by(User.role)
    )
    users_by_role = {row[0]: row[1] for row in role_result.fetchall()}

    # 标签使用统计（发布最多的标签 Top 8）
    tag_result = await db.execute(
        select(MessageTagLink.tag_key, func.count(MessageTagLink.id))
        .group_by(MessageTagLink.tag_key)
        .order_by(func.count(MessageTagLink.id).desc())
        .limit(8)
    )
    tag_stats = {row[0]: row[1] for row in tag_result.fetchall()}

    # 标签名映射
    tag_name_result = await db.execute(select(MessageTag.tag_key, MessageTag.tag_name))
    tag_names = {row[0]: row[1] for row in tag_name_result.fetchall()}

    # 最近 7 天每日发布数
    recent_result = await db.execute(select(func.date(Message.published_at).label("d"), func.count(Message.id))
        .where(Message.published_at >= func.date_sub(func.now(), text("INTERVAL 7 DAY")))
        .group_by("d").order_by("d"))
    recent_daily = [{"date": str(row[0]), "count": row[1]} for row in recent_result.fetchall()]

    return {
        "total_messages": total_messages,
        "today_messages": today_messages,
        "users_by_role": users_by_role,
        "tag_stats": [{"tag_key": k, "tag_name": tag_names.get(k, k), "count": v} for k, v in sorted(tag_stats.items(), key=lambda x: -x[1])],
        "recent_daily": recent_daily,
    }
