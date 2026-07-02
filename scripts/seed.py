import asyncio

from loguru import logger

from app.core.db import _async_session_factory
from app.models.books import Book
from app.models.contributor import Contributor
from app.models.user import User
from app.services.security import hash_password
from scripts.seed_data import DEV_BOOKS, DEV_CONTRIBUTORS, DEV_USERS, upsert_by


async def main() -> None:
    async with _async_session_factory() as session:
        await upsert_by(session, Contributor, "slug", DEV_CONTRIBUTORS)
        await upsert_by(session, Book, "title", DEV_BOOKS)

        user_rows = [
            {**row, "password_hash": hash_password(row["password"])}
            for row in DEV_USERS
        ]
        for row in user_rows:
            del row["password"]
        await upsert_by(session, User, "email", user_rows)

        await session.commit()
    logger.info("Seed data loaded.")


if __name__ == "__main__":
    asyncio.run(main())
