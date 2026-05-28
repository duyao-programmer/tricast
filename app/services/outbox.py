# ============================================================================
# 事务发件箱后台发布器
# ============================================================================
import asyncio
import json as _json
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models.message import Outbox
from app.services.rabbitmq import publish_message
from loguru import logger

# ============================================================================
# 发件箱轮询间隔（秒）
# ============================================================================
OUTBOX_POLL_INTERVAL = 2

# 最大重试次数
MAX_RETRY_COUNT = 3


async def run_outbox_publisher(shutdown_event: asyncio.Event):
    """
    事务发件箱发布器：轮询 pending 记录并发布到 RabbitMQ

    Args:
        shutdown_event: 关闭信号
    """
    logger.info("Outbox 发布器启动，轮询间隔 {} 秒", OUTBOX_POLL_INTERVAL)

    while not shutdown_event.is_set():
        try:
            async with AsyncSessionLocal() as session:
                # 查询 pending 记录
                stmt = (
                    select(Outbox)
                    .where(Outbox.status == "pending")
                    .order_by(Outbox.id)
                    .limit(10)
                )
                result = await session.execute(stmt)
                pending_items = result.scalars().all()

                for item in pending_items:
                    if shutdown_event.is_set():
                        break

                    try:
                        # 发布到 RabbitMQ（含 Publisher Confirms）
                        event_json = _json.dumps(item.payload)

                        await publish_message(event_json)

                        # 标记为已发布
                        await session.execute(
                            update(Outbox)
                            .where(Outbox.id == item.id)
                            .values(status="published")
                        )
                        await session.commit()
                        logger.info("Outbox #{} 发布成功", item.id)

                    except Exception as exc:
                        logger.error("Outbox #{} 发布失败: {}", item.id, exc)

                        # 更新重试计数
                        new_retry = item.retry_count + 1
                        new_status = "pending" if new_retry < MAX_RETRY_COUNT else "failed"

                        await session.execute(
                            update(Outbox)
                            .where(Outbox.id == item.id)
                            .values(
                                retry_count=new_retry,
                                status=new_status,
                                last_error=str(exc)[:1000],
                            )
                        )
                        await session.commit()

        except Exception as exc:
            logger.exception("Outbox 发布器异常: {}", exc)

        # 等待下次轮询
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=OUTBOX_POLL_INTERVAL)
        except asyncio.TimeoutError:
            pass  # 正常超时，继续下一轮

    logger.info("Outbox 发布器已关闭")
