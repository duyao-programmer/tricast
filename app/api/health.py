# ============================================================================
# 健康检查端点
# ============================================================================
from fastapi import APIRouter
from sqlalchemy import text
from app.database import AsyncSessionLocal
import aio_pika
from app.config import settings
from loguru import logger

router = APIRouter(tags=["健康检查"])


@router.get("/health")
async def health_check():
    """返回数据库和 RabbitMQ 连接状态"""
    health = {
        "status": "ok",
        "database": "unknown",
        "rabbitmq": "unknown",
    }

    # 数据库连接检查
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        health["database"] = "connected"
    except Exception as e:
        health["status"] = "degraded"
        health["database"] = f"error: {e}"
        logger.error("健康检查：数据库连接失败 - {}", e)

    # RabbitMQ 连接检查
    try:
        connection = await aio_pika.connect_robust(
            settings.rabbitmq_url,
            timeout=5,
        )
        await connection.close()
        health["rabbitmq"] = "connected"
    except Exception as e:
        health["status"] = "degraded"
        health["rabbitmq"] = f"error: {e}"
        logger.error("健康检查：RabbitMQ 连接失败 - {}", e)

    if health["status"] == "degraded":
        from fastapi import status
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=health)

    return health
