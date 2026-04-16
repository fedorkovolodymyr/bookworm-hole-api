from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
    async_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
