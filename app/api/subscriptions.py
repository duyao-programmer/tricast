# ============================================================================
# 订阅管理 API
# ============================================================================
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.mysql import insert as mysql_insert
from loguru import logger

from app.database import get_db
from app.models.subscription import MessageTag, UserSubscription
from app.schemas.subscription import (
    TagInfo, UserSubscriptionItem, UserSubscriptionsResponse,
    SubscriptionUpdateRequest,
)
from app.middleware.auth import get_current_user

router = APIRouter(tags=["订阅"])


@router.get("/api/messages/tags", response_model=list[TagInfo])
async def list_tags(db: AsyncSession = Depends(get_db)):
    """获取所有可用标签（公开接口）"""
    stmt = select(MessageTag).order_by(MessageTag.sort_order)
    result = await db.execute(stmt)
    tags = result.scalars().all()
    return [
        TagInfo(
            tag_key=t.tag_key,
            tag_name=t.tag_name,
            category=t.category,
            is_default=t.is_default,
            sort_order=t.sort_order,
        )
        for t in tags
    ]


@router.get("/api/subscriptions", response_model=UserSubscriptionsResponse)
async def get_subscriptions(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户对所有标签的订阅状态"""
    user_id = current_user["user_id"]

    # 获取所有标签
    tag_stmt = select(MessageTag).order_by(MessageTag.sort_order)
    tag_result = await db.execute(tag_stmt)
    all_tags = tag_result.scalars().all()

    # 获取用户的订阅记录
    sub_stmt = select(UserSubscription).where(UserSubscription.user_id == user_id)
    sub_result = await db.execute(sub_stmt)
    user_subs = {s.tag_key: s.subscribed for s in sub_result.scalars().all()}

    items = []
    for tag in all_tags:
        # 如果用户从未订阅过，默认订阅 is_default 标签
        if tag.tag_key in user_subs:
            subscribed = user_subs[tag.tag_key]
        else:
            subscribed = tag.is_default

        items.append(UserSubscriptionItem(
            tag_key=tag.tag_key,
            tag_name=tag.tag_name,
            category=tag.category,
            is_default=tag.is_default,
            subscribed=subscribed,
        ))

    return UserSubscriptionsResponse(tags=items)


@router.put("/api/subscriptions")
async def update_subscriptions(
    body: SubscriptionUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量更新订阅状态"""
    user_id = current_user["user_id"]
    count = 0

    for item in body.subscriptions:
        tag_key = item.get("tag_key")
        subscribed = item.get("subscribed", True)
        if not tag_key:
            continue

        stmt = mysql_insert(UserSubscription).values(
            user_id=user_id,
            tag_key=tag_key,
            subscribed=subscribed,
        )
        stmt = stmt.on_duplicate_key_update(subscribed=stmt.inserted.subscribed)
        await db.execute(stmt)
        count += 1

    await db.commit()
    logger.info("用户 {} 更新了 {} 项订阅", current_user["username"], count)
    return {"message": "订阅已更新", "count": count}
