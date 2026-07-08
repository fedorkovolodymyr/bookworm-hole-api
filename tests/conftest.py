import asyncio
import os
from collections.abc import AsyncIterator, Callable
from pathlib import Path

os.environ.setdefault("POSTGRES_DB", "bookwormhole_test")

import pytest
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
from app.core.config import get_settings, settings
from app.core.db import async_engine, get_session
from app.core.deps import get_current_user
from app.main import app
from app.models.user import User

_ROOT = Path(__file__).resolve().parent.parent


async def _create_database_if_missing() -> None:
    pg = settings.postgres_settings
    maintenance_url = pg.DB_URI.rsplit("/", 1)[0] + "/postgres"
    engine = create_async_engine(maintenance_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": pg.db}
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{pg.db}"'))
    finally:
        await engine.dispose()


def pytest_configure(config: pytest.Config) -> None:
    asyncio.run(_create_database_if_missing())
    alembic_cfg = Config(str(_ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with async_engine.connect() as conn:
        trans = await conn.begin()
        session_factory = async_sessionmaker(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _get_session_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _get_session_override
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.pop(get_session, None)


def _make_user(role: str) -> User:
    return User(
        email=f"{role}@example.com",
        username=role,
        display_name=role.title(),
        is_admin=role == "admin",
    )


@pytest.fixture
async def auth_client(
    async_client: AsyncClient,
) -> AsyncIterator[Callable[[str], AsyncClient]]:
    def _as_role(role: str) -> AsyncClient:
        app.dependency_overrides[get_current_user] = lambda: _make_user(role)
        return async_client

    yield _as_role
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def admin_client(auth_client: Callable[[str], AsyncClient]) -> AsyncClient:
    return auth_client("admin")


@pytest.fixture
async def reader_client(auth_client: Callable[[str], AsyncClient]) -> AsyncClient:
    return auth_client("reader")
