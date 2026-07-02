import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import get_session


async def test_get_session_can_select_1():
    try:
        async for session in get_session():
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
    except (SQLAlchemyError, OSError) as exc:
        pytest.skip(f"database unavailable: {exc}")
