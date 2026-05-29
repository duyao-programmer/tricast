# ============================================================================
# Redis 连接管理 + 缓存工具函数
# ============================================================================
import json
import redis.asyncio as aioredis
from app.config import settings
from loguru import logger

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """获取 Redis 连接（单例惰性初始化）"""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        await _redis.ping()
        logger.info("Redis 连接成功: {}", settings.redis_url)
    return _redis


async def close_redis():
    """关闭 Redis 连接"""
    global _redis
    if _redis:
        await _redis.close()
        _redis = None
        logger.info("Redis 连接已关闭")


# ============================================================================
# 用户角色缓存
# ============================================================================
async def cache_user_role(user_id: int, data: dict, ttl: int = 30):
    r = await get_redis()
    await r.setex(f"user:{user_id}:role", ttl, json.dumps(data, ensure_ascii=False))


async def get_cached_user_role(user_id: int) -> dict | None:
    r = await get_redis()
    raw = await r.get(f"user:{user_id}:role")
    return json.loads(raw) if raw else None


async def invalidate_user_role(user_id: int):
    r = await get_redis()
    await r.delete(f"user:{user_id}:role")


# ============================================================================
# JWT 黑名单
# ============================================================================
async def blacklist_token(jti: str, ttl: int):
    r = await get_redis()
    await r.setex(f"blacklist:{jti}", ttl, "1")


async def is_token_blacklisted(jti: str) -> bool:
    r = await get_redis()
    return await r.exists(f"blacklist:{jti}") > 0


# ============================================================================
# 死信持久化
# ============================================================================
async def push_dead_letter(record: dict):
    r = await get_redis()
    await r.rpush("dead_letters", json.dumps(record, ensure_ascii=False))
    await r.ltrim("dead_letters", -200, -1)


async def get_dead_letters() -> list[dict]:
    r = await get_redis()
    items = await r.lrange("dead_letters", 0, -1)
    return [json.loads(item) for item in items]


# ============================================================================
# 权限缓存
# ============================================================================
async def cache_permissions(user_id: int, data: dict, ttl: int = 60):
    r = await get_redis()
    await r.setex(f"user_perms:{user_id}", ttl, json.dumps(data, ensure_ascii=False))


async def get_cached_permissions(user_id: int) -> dict | None:
    r = await get_redis()
    raw = await r.get(f"user_perms:{user_id}")
    return json.loads(raw) if raw else None


async def invalidate_permissions(user_id: int):
    r = await get_redis()
    await r.delete(f"user_perms:{user_id}")
