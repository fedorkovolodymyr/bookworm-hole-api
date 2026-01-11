from typing import AsyncIterator

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from app.core.confg import settings

async_engine = create_async_engine(
    settings.postgres_settings.DB_URI,
    pool_pre_ping=True,
    echo=settings.postgres_settings.echo_sql,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autoflush=False,
    future=True,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            logger.exception(f"Database error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
