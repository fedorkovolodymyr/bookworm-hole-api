from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

async_engine = create_async_engine(
    settings.postgres_settings.DB_URI,
    pool_pre_ping=True,
    echo=settings.postgres_settings.echo_sql,
    pool_size=settings.postgres_settings.pool_size,
    max_overflow=settings.postgres_settings.max_overflow,
)

_async_session_factory = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:  # noqa: BLE001 -- session rollback boundary, must catch any error
            await session.rollback()
            raise
