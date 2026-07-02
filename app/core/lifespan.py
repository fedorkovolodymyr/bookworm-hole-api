import sys

from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from loguru import logger

from app.core.config import get_settings
from app.core.db import async_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    sink_id = logger.add(sys.stderr, level=get_settings().app_settings.log_level)
    logger.info("Starting application...")
    yield
    logger.info("Shutting down application...")
    try:
        await async_engine.dispose()
    finally:
        logger.remove(sink_id)
