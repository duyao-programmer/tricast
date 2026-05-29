# ============================================================================
# 消息查询接口（角色分级 Schema 分发）
# ============================================================================
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
import csv, io, json as _json
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from loguru import logger

from app.database import get_db
from app.models.message import Message, MessageReceipt
from app.models.subscription import UserSubscription, MessageTagLink
from app.models.user import User
from app.services.redis import get_dead_letters
from app.middleware.auth import get_current_user, require_role
from app.schemas.message import (
    MessageAdminResponse, MessageAdvancedResponse, MessageRegularResponse,
    ReceiptResponse, MessageStatsResponse, ChannelStats,
)
from app.services.crypto import decrypt_to_dict

router = APIRouter(prefix="/api/messages", tags=["消息"])


def _build_admin_response(message: Message) -> MessageAdminResponse:
    """构建管理员（角色1）完整响应"""
    secret_data = None
    if message.secret_data_encrypted:
        try:
            secret_data = decrypt_to_dict(message.secret_data_encrypted)
        except Exception as e:
            logger.warning("消息 #{} 解密 secret_data 失败: {}", message.id, e)
            secret_data = {"error": "解密失败"}

    receipts = []
    if hasattr(message, 'receipts') and message.receipts:
        for r in message.receipts:
            receipts.append(ReceiptResponse(
                consumer_role=r.consumer_role,
                channel=r.channel,
                received_at=r.received_at.isoformat() if r.received_at else None,
                processing_time_ms=r.processing_time_ms,
            ))

    publisher_name = None
    if hasattr(message, 'publisher') and message.publisher:
        publisher_name = message.publisher.username

    return MessageAdminResponse(
        id=message.id,
        title=message.title,
        content=message.content,
        published_at=message.published_at.isoformat() if message.published_at else None,
        secret_data=secret_data,
        publisher=publisher_name,
        channel=f"msg.fanout/{message.id}",
        receipts=receipts,
        tags=getattr(message, 'tags', []),
    )


def _build_advanced_response(message: Message) -> MessageAdvancedResponse:
    """构建高级用户（角色2）响应"""
    content = message.content
    if len(content) > 50:
        content = content[:50] + "...[truncated]"

    publisher_name = None
    if hasattr(message, 'publisher') and message.publisher:
        publisher_name = message.publisher.username

    return MessageAdvancedResponse(
        id=message.id,
        title=message.title,
        content=content,
        published_at=message.published_at.isoformat() if message.published_at else None,
        publisher=publisher_name,
        channel=f"queue.advanced/{message.id}",
        tags=getattr(message, 'tags', []),
    )


def _build_regular_response(message: Message) -> MessageRegularResponse:
    """构建普通用户（角色3）响应"""
    return MessageRegularResponse(
        id=message.id,
        title=message.title,
        published_at=message.published_at.isoformat() if message.published_at else None,
        tags=getattr(message, 'tags', []),
    )


# 角色到构建函数的映射
_RESPONSE_BUILDERS = {
    "admin": (_build_admin_response, MessageAdminResponse),
    "advanced": (_build_advanced_response, MessageAdvancedResponse),
    "regular": (_build_regular_response, MessageRegularResponse),
}


@router.get("")
async def list_messages(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    subscribed: bool = Query(False, description="仅显示已订阅标签的消息"),
    start_date: date | None = Query(None, description="开始日期（YYYY-MM-DD）"),
    end_date: date | None = Query(None, description="结束日期（YYYY-MM-DD）"),
    filter_tags: str | None = Query(None, description="筛选标签，逗号分隔如 tech,hr"),
    keyword: str | None = Query(None, description="搜索关键词（标题+内容）"),
    publisher_role: str | None = Query(None, description="按发布者角色筛选: admin/advanced/regular"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """消息列表（支持按时间范围、标签筛选）"""
    role = current_user["role"]
    user_id = current_user["user_id"]
    offset = (page - 1) * page_size

    stmt = select(Message).order_by(Message.published_at.desc())

    # 按发布者角色筛选
    if publisher_role:
        sub = select(User.id).where(User.role == publisher_role, User.is_active == True).subquery()
        stmt = stmt.where(Message.publisher_id.in_(select(sub)))

    # 关键词搜索（标题 + 内容）
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Message.title.like(like), Message.content.like(like)))

    # 时间范围筛选
    if start_date:
        stmt = stmt.where(Message.published_at >= start_date)
    if end_date:
        stmt = stmt.where(Message.published_at < end_date)

    # 标签筛选（指定标签，与订阅模式互斥）
    if filter_tags and not subscribed:
        tag_keys = [t.strip() for t in filter_tags.split(",") if t.strip()]
        if tag_keys:
            tag_msg_stmt = (
                select(MessageTagLink.message_id.distinct())
                .where(MessageTagLink.tag_key.in_(tag_keys))
                .subquery()
            )
            stmt = stmt.where(Message.id.in_(select(tag_msg_stmt)))

    # 订阅筛选（管理员忽略）
    if subscribed and role != "admin":
        # 获取用户订阅的标签
        sub_stmt = select(UserSubscription.tag_key).where(
            UserSubscription.user_id == user_id,
            UserSubscription.subscribed == True,
        )
        sub_result = await db.execute(sub_stmt)
        subscribed_tags = [row[0] for row in sub_result.fetchall()]

        if subscribed_tags:
            stmt = stmt.where(
                Message.id.in_(
                    select(MessageTagLink.message_id.distinct())
                    .where(MessageTagLink.tag_key.in_(subscribed_tags))
                )
            )
        else:
            stmt = stmt.where(Message.id == -1)

    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    messages = result.scalars().all()

    # 加载所有消息的标签
    if messages:
        message_ids = [m.id for m in messages]
        tag_stmt = select(MessageTagLink).where(MessageTagLink.message_id.in_(message_ids))
        tag_result = await db.execute(tag_stmt)
        tag_links = tag_result.scalars().all()
        tags_map = {}
        for tl in tag_links:
            tags_map.setdefault(tl.message_id, []).append(tl.tag_key)
        for m in messages:
            m.tags = tags_map.get(m.id, [])

    if role == "admin":
        message_ids = [m.id for m in messages]
        message_ids = [m.id for m in messages]
        if message_ids:
            receipt_stmt = (
                select(MessageReceipt)
                .where(MessageReceipt.message_id.in_(message_ids))
            )
            receipt_result = await db.execute(receipt_stmt)
            all_receipts = receipt_result.scalars().all()

            receipts_map = {}
            for r in all_receipts:
                receipts_map.setdefault(r.message_id, []).append(r)

            for m in messages:
                m.receipts = receipts_map.get(m.id, [])
                m.publisher = None

    builder, _ = _RESPONSE_BUILDERS[role]
    items = [builder(m) for m in messages]

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "role": role,
    }


# ⚠️ /stats 和 /export 必须在 /{message_id} 之前注册
@router.get("/export")
async def export_messages(
    fmt: str = Query("json", description="导出格式: csv 或 json"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """导出所有消息为 CSV 或 JSON（仅管理员）"""
    stmt = select(Message).order_by(Message.published_at.desc())
    result = await db.execute(stmt)
    messages = result.scalars().all()
    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "标题", "内容", "发布者ID", "发布时间"])
        for m in messages:
            writer.writerow([m.id, m.title, m.content, m.publisher_id,
                m.published_at.isoformat() if m.published_at else ""])
        return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=messages.csv"})
    else:
        data = [{"id": m.id, "title": m.title, "content": m.content,
                 "publisher_id": m.publisher_id,
                 "published_at": m.published_at.isoformat() if m.published_at else None} for m in messages]
        buf = io.StringIO(); _json.dump(data, buf, ensure_ascii=False, indent=2)
        return StreamingResponse(iter([buf.getvalue()]), media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=messages.json"})

@router.get("/stats", response_model=list[MessageStatsResponse])
async def get_message_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """
    消息耗时统计（仅管理员）
    返回最近 10 条消息在各通道的耗时统计
    """
    stmt = select(Message).order_by(Message.published_at.desc()).limit(10)
    result = await db.execute(stmt)
    messages = result.scalars().all()

    stats_list = []
    for message in messages:
        receipt_stmt = (
            select(MessageReceipt)
            .where(MessageReceipt.message_id == message.id)
        )
        receipt_result = await db.execute(receipt_stmt)
        receipts = receipt_result.scalars().all()

        channels_stats = {}
        for r in receipts:
            ch = r.channel
            if ch not in channels_stats:
                channels_stats[ch] = []
            if r.processing_time_ms is not None:
                channels_stats[ch].append(r.processing_time_ms)

        channel_list = []
        for ch, times in channels_stats.items():
            if times:
                channel_list.append(ChannelStats(
                    channel=ch,
                    count=len(times),
                    min_ms=min(times),
                    max_ms=max(times),
                    avg_ms=round(sum(times) / len(times), 2),
                ))
            else:
                channel_list.append(ChannelStats(
                    channel=ch,
                    count=0,
                ))

        stats_list.append(MessageStatsResponse(
            message_id=message.id,
            title=message.title,
            channels=channel_list,
        ))

    return stats_list


@router.get("/dead")
async def list_dead_letters(
    request: Request,
    current_user: dict = Depends(require_role("admin")),
):
    """死信队列内容（仅管理员）—— 从 Redis 返回最近记录的 200 条死信"""
    items = await get_dead_letters()
    return {"total": len(items), "items": items}


@router.get("/{message_id}")
async def get_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """单条消息详情（按角色返回不同字段）"""
    role = current_user["role"]

    stmt = select(Message).where(Message.id == message_id)
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在",
        )

    # 加载标签
    tag_stmt = select(MessageTagLink).where(MessageTagLink.message_id == message_id)
    tag_result = await db.execute(tag_stmt)
    message.tags = [t.tag_key for t in tag_result.scalars().all()]

    if role in ("admin", "advanced"):
        publisher_stmt = select(User).where(User.id == message.publisher_id)
        pub_result = await db.execute(publisher_stmt)
        message.publisher = pub_result.scalar_one_or_none()

    if role == "admin":
        receipt_stmt = (
            select(MessageReceipt)
            .where(MessageReceipt.message_id == message_id)
        )
        receipt_result = await db.execute(receipt_stmt)
        message.receipts = receipt_result.scalars().all()

    builder, _ = _RESPONSE_BUILDERS[role]
    return builder(message)
