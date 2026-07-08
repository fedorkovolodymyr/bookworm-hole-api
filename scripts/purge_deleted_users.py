import asyncio

from loguru import logger

from app.core.db import async_session_factory
from app.repositories.account_deletion_repository import AccountDeletionRepository
from app.repositories.user_repository import UserRepository
from app.services.account_deletion_service import AccountDeletionService


async def main() -> None:
    async with async_session_factory() as session:
        service = AccountDeletionService(
            UserRepository(session), AccountDeletionRepository(session)
        )
        summary = await service.purge_deleted_users()

    logger.info(f"Account purge complete: purged={summary.purged}")


if __name__ == "__main__":
    asyncio.run(main())
