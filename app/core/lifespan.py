import sentry_sdk
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from loguru import logger

from app.core.config import get_settings
from app.core.db import async_engine
from app.core.logging import configure_logging
from app.core.redis import close_redis_pool, init_redis_pool
from app.services.websocket_manager import websocket_manager


def _init_sentry() -> None:
    sentry_settings = get_settings().sentry_settings
    if not sentry_settings.dsn:
        logger.info("Sentry DSN not set, error tracking disabled")
        return
    sentry_sdk.init(
        dsn=sentry_settings.dsn,
        environment=get_settings().app_settings.app_env,
        traces_sample_rate=sentry_settings.traces_sample_rate,
        profiles_sample_rate=sentry_settings.profiles_sample_rate,
        send_default_pii=False,
    )
    logger.info("Sentry error tracking initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    sink_id = configure_logging(get_settings().app_settings.log_level)
    _init_sentry()
    await init_redis_pool()
    logger.info("Starting application...")
    yield
    logger.info("Shutting down application...")
    try:
        await websocket_manager.shutdown()
        await close_redis_pool()
        await async_engine.dispose()
    finally:
        logger.remove(sink_id)
