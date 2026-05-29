# ============================================================================
# 消息发布接口（管理员专用）
# ============================================================================
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db
from app.models.message import Message, Outbox
from app.models.subscription import MessageTagLink
from app.models.user import User
from app.middleware.auth import require_role
from app.schemas.message import (
    MessagePublishRequest, BatchPublishRequest,
    PublishResponse, BatchPublishResponse,
    MessagePublishedEvent,
)
from app.services.crypto import encrypt_dict

router = APIRouter(prefix="/api/publish", tags=["发布"])


async def _create_message_and_outbox(
    db: AsyncSession,
    req: MessagePublishRequest,
    publisher_id: int,
) -> tuple[int, int]:
    """
    在数据库事务中创建消息和发件箱记录

    Returns:
        (message_id, outbox_id)
    """
    # 加密 secret_data
    secret_data_encrypted = None
    if req.secret_data:
        secret_data_encrypted = encrypt_dict(req.secret_data)

    # 创建消息
    message = Message(
        title=req.title,
        content=req.content,
        secret_data_encrypted=secret_data_encrypted,
        publisher_id=publisher_id,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)

    # 构造 MessagePublishedEvent
    event = MessagePublishedEvent(
        message_id=message.id,
        title=message.title,
        content=message.content,
        secret_data_encrypted=secret_data_encrypted,
        publisher_id=publisher_id,
        published_at=message.published_at.isoformat() if message.published_at else "",
    )

    # 创建发件箱记录
    outbox = Outbox(
        aggregate_type="message",
        aggregate_id=message.id,
        event_type="message_published",
        payload=event.model_dump(),
        status="pending",
    )
    db.add(outbox)
    await db.flush()
    await db.refresh(outbox)

    # 写入消息-标签关联
    if req.tags:
        for tag_key in req.tags:
            db.add(MessageTagLink(message_id=message.id, tag_key=tag_key))

    return message.id, outbox.id


@router.post("", response_model=PublishResponse, status_code=status.HTTP_201_CREATED)
async def publish_message(
    body: MessagePublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """发布单条消息（仅管理员）"""
    publisher_id = current_user["user_id"]

    try:
        message_id, outbox_id = await _create_message_and_outbox(db, body, publisher_id)
        await db.commit()

        logger.info("管理员 {} 发布消息 #{}", current_user["username"], message_id)

        return PublishResponse(
            message_id=message_id,
            status="pending",
            outbox_id=outbox_id,
        )
    except Exception as e:
        await db.rollback()
        logger.error("消息发布失败: {}", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"消息发布失败: {e}",
        )


@router.post("/batch", response_model=BatchPublishResponse, status_code=status.HTTP_201_CREATED)
async def publish_batch(
    body: BatchPublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """批量发布消息（仅管理员，最多 10 条）"""
    publisher_id = current_user["user_id"]

    results = []
    try:
        for req in body.messages:
            message_id, outbox_id = await _create_message_and_outbox(db, req, publisher_id)
            results.append(PublishResponse(
                message_id=message_id,
                status="pending",
                outbox_id=outbox_id,
            ))

        await db.commit()
        logger.info("管理员 {} 批量发布 {} 条消息", current_user["username"], len(results))

        return BatchPublishResponse(total=len(results), results=results)
    except Exception as e:
        await db.rollback()
        logger.error("批量发布失败: {}", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量发布失败: {e}",
        )
