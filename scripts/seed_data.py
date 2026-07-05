from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

DEV_CONTRIBUTORS: list[dict[str, Any]] = [
    {
        "full_name": "Ada Lovelace",
        "sort_name": "Lovelace, Ada",
        "slug": "ada-lovelace",
        "bio": (
            "Mathematician and writer, known for work on Babbage's Analytical Engine."
        ),
    },
    {
        "full_name": "Jorge Luis Borges",
        "sort_name": "Borges, Jorge Luis",
        "slug": "jorge-luis-borges",
        "bio": "Argentine short-story writer, essayist, and poet.",
    },
]

DEV_BOOKS: list[dict[str, Any]] = [
    {
        "title": "The Library of Babel",
        "description": "A short story conceiving of a universe as a vast library.",
    },
    {
        "title": "Notes on the Analytical Engine",
        "description": "Notes describing an algorithm for the Analytical Engine.",
    },
]

DEV_USERS: list[dict[str, Any]] = [
    {
        "email": "dev@bookwormhole.test",
        "username": "dev",
        "display_name": "Dev User",
        "password": "dev-password-123",
    },
]


async def upsert_by[ModelT: SQLModel](
    session: AsyncSession,
    model: type[ModelT],
    field: str,
    rows: list[dict[str, Any]],
) -> list[ModelT]:
    """Insert rows missing from the table, matched by a unique field. Safe to re-run."""
    instances: list[ModelT] = []
    for row in rows:
        existing = await session.execute(
            select(model).where(getattr(model, field) == row[field])
        )
        instance = existing.scalars().first()
        if instance is None:
            instance = model(**row)
            session.add(instance)
        instances.append(instance)
    await session.flush()
    return instances
