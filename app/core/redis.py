from arq import create_pool
from arq.connections import ArqRedis
from arq.connections import RedisSettings as ArqRedisSettings

from app.core.config import settings

_redis_pool: ArqRedis | None = None


def _arq_redis_settings() -> ArqRedisSettings:
    redis_settings = settings.redis_settings
    return ArqRedisSettings(
        host=redis_settings.host, port=redis_settings.port, database=redis_settings.db
    )


async def init_redis_pool() -> ArqRedis:
    global _redis_pool
    _redis_pool = await create_pool(_arq_redis_settings())
    return _redis_pool


async def close_redis_pool() -> None:
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None


def get_redis_pool() -> ArqRedis:
    if _redis_pool is None:
        raise RuntimeError("Redis pool not initialized")
    return _redis_pool
