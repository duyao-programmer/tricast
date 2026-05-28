# ============================================================================
# FastAPI 入口，lifespan 管理全部后台协程
# ============================================================================
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from loguru import logger
import sys

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.rabbitmq import (
    setup_rabbitmq_infrastructure,
    consume_queue,
    QUEUE_ADMIN,
    QUEUE_ADVANCED,
    QUEUE_REGULAR,
)
from app.services.outbox import run_outbox_publisher
from app.api import health, auth, publish, messages

# ============================================================================
# 日志配置
# ============================================================================
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="DEBUG" if settings.app_debug else "INFO",
)


# ============================================================================
# 消费者消息处理回调
# ============================================================================
async def handle_message(body: bytes, consumer_role: str):
    """
    消费者消息处理回调：解析消息 → 写入 message_receipts

    Args:
        body: 消息体（MessagePublishedEvent JSON）
        consumer_role: 消费者角色
    """
    import json
    from datetime import datetime, timezone
    from sqlalchemy.dialects.mysql import insert as mysql_insert
    from app.models.message import MessageReceipt, Message
    from app.schemas.message import MessagePublishedEvent

    event_data = json.loads(body.decode("utf-8"))

    # Pydantic 校验
    event = MessagePublishedEvent.model_validate(event_data)

    # 计算处理耗时（published_at 是 naive datetime，需加 UTC 时区）
    now = datetime.now(timezone.utc)
    if event.published_at:
        published_at = datetime.fromisoformat(event.published_at).replace(tzinfo=timezone.utc)
    else:
        published_at = now
    processing_time_ms = int((now - published_at).total_seconds() * 1000)

    # 写入回执（带重试和幂等性处理）
    for attempt in range(3):
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    # 使用 INSERT IGNORE 风格的 upsert 实现幂等性
                    receipt = MessageReceipt(
                        message_id=event.message_id,
                        consumer_role=consumer_role,
                        channel=f"{consumer_role}_channel",
                        received_at=datetime.now(timezone.utc),
                        processing_time_ms=processing_time_ms,
                    )
                    session.add(receipt)
                    try:
                        await session.flush()
                    except Exception:
                        # 唯一约束冲突 = 重复消息，直接忽略
                        logger.warning(
                            "消费者 [{}] 收到重复消息 #{}，跳过",
                            consumer_role, event.message_id,
                        )
                        await session.rollback()
                        return
            break  # 写入成功
        except Exception as exc:
            logger.warning(
                "消费者 [{}] 写入回执失败（第 {} 次）: {}",
                consumer_role, attempt + 1, exc,
            )
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
            else:
                raise  # 3 次都失败，抛给外层进入死信

    logger.info(
        "消费者 [{}] 处理消息 #{}, 耗时 {}ms",
        consumer_role, event.message_id, processing_time_ms,
    )


# ============================================================================
# Lifespan 管理
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动/关闭后台协程"""
    logger.info("=" * 60)
    logger.info("TriCast - 消息发布订阅系统启动中...")
    logger.info("=" * 60)

    # 创建关闭信号
    shutdown_event = asyncio.Event()

    # 初始化 RabbitMQ 基础设施
    try:
        await setup_rabbitmq_infrastructure()
    except Exception as e:
        logger.error("RabbitMQ 基础设施初始化失败: {}", e)
        raise

    # 启动 outbox 发布器
    outbox_task = asyncio.create_task(
        run_outbox_publisher(shutdown_event),
        name="outbox_publisher",
    )

    # 启动三个消费者协程
    consumer_tasks = []
    for queue_name, consumer_role in [
        (QUEUE_ADMIN, "admin"),
        (QUEUE_ADVANCED, "advanced"),
        (QUEUE_REGULAR, "regular"),
    ]:
        task = asyncio.create_task(
            consume_queue(queue_name, consumer_role, handle_message, shutdown_event),
            name=f"consumer_{consumer_role}",
        )
        consumer_tasks.append(task)

    logger.info("所有后台协程已启动（outbox 发布器 + {} 个消费者）", len(consumer_tasks))
    logger.info("FastAPI 服务已就绪: http://0.0.0.0:8000")
    logger.info("API 文档: http://0.0.0.0:8000/docs")

    # 将协程引用保存到 app.state，供健康监控使用
    app.state.consumer_tasks = consumer_tasks
    app.state.outbox_task = outbox_task

    yield

    # ========================================================================
    # 关闭流程
    # ========================================================================
    logger.info("正在关闭所有后台协程...")
    shutdown_event.set()

    all_tasks = [outbox_task] + consumer_tasks
    for task in all_tasks:
        if not task.done():
            task.cancel()

    # 等待协程优雅退出（最多 15 秒）
    try:
        await asyncio.wait_for(
            asyncio.gather(*all_tasks, return_exceptions=True),
            timeout=15,
        )
    except asyncio.TimeoutError:
        logger.warning("后台协程未在 15 秒内退出，强制取消")

    logger.info("应用已关闭")


# ============================================================================
# FastAPI 应用实例
# ============================================================================
app = FastAPI(
    title="TriCast - 消息发布订阅系统",
    description="基于 RabbitMQ + FastAPI + MySQL 的三角色消息发布订阅演示系统 (Tri-role + Fanout Cast)",
    version="1.0.0",
    lifespan=lifespan,
)

# 注册路由
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(publish.router)
app.include_router(messages.router)


# ============================================================================
# 健康监控端点：检查消费者协程状态
# ============================================================================
@app.get("/health/consumers")
async def check_consumers():
    """检查消费者协程状态（用于监控自动重建）"""
    tasks = getattr(app.state, "consumer_tasks", [])
    result = {}
    for task in tasks:
        name = task.get_name()
        if task.done():
            exc = task.exception()
            result[name] = {
                "status": "crashed",
                "error": str(exc) if exc else "正常退出",
            }
        else:
            result[name] = {"status": "running"}
    return result
