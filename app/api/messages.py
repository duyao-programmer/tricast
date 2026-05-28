# ============================================================================
# 消息查询接口（角色分级 Schema 分发）
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from loguru import logger

from app.database import get_db
from app.models.message import Message, MessageReceipt
from app.models.user import User
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
    )


def _build_regular_response(message: Message) -> MessageRegularResponse:
    """构建普通用户（角色3）响应"""
    return MessageRegularResponse(
        id=message.id,
        title=message.title,
        published_at=message.published_at.isoformat() if message.published_at else None,
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
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """消息列表（按角色返回不同字段）"""
    role = current_user["role"]
    offset = (page - 1) * page_size

    stmt = select(Message).order_by(Message.published_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    messages = result.scalars().all()

    if role == "admin":
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


# ⚠️ /stats 必须在 /{message_id} 之前注册，否则 "stats" 会被当作 message_id 解析
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
    """死信队列内容（仅管理员）—— 从内存返回最近记录的 200 条死信"""
    store: list = getattr(request.app.state, "dead_letter_store", [])
    return {"total": len(store), "items": store}


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
