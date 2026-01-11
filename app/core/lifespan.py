import asyncio
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from loguru import logger
from sqlalchemy import inspect

from app.models import Base  # required to register models' metadata
from app.core.db import async_engine


async def init_db():
    logger.info("Initializing database...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_table_names():

    try:
        async with async_engine.connect() as conn:

            def _get_tables(sync_conn):
                inspector = inspect(sync_conn)
                return inspector.get_table_names()

            tables = await conn.run_sync(_get_tables)
            logger.info(f"Existing tables in database: {tables}")
            return tables
    except Exception as e:
        logger.error(f"Failed to get table names: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await asyncio.sleep(1)
    await get_table_names()
    yield
    logger.info("Shutting down application...")
