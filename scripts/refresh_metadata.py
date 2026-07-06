import argparse
import asyncio

from loguru import logger

from app.core.db import async_session_factory
from app.repositories.release_repository import ReleaseRepository
from app.services.refresh_metadata_service import RefreshMetadataService


async def main(older_than_days: int) -> None:
    async with async_session_factory() as session:
        service = RefreshMetadataService(session, ReleaseRepository(session))
        summary = await service.refresh_stale_releases(older_than_days)

    logger.info(
        f"Metadata refresh complete: refreshed={summary.refreshed} "
        f"conflicts={summary.conflicts} skipped={summary.skipped}"
    )
    for detail in summary.conflict_details:
        logger.warning(detail)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Refresh stale release metadata from external sources."
    )
    parser.add_argument(
        "--older-than-days",
        type=int,
        default=30,
        help="Refresh releases whose last external sync is older than N days (default: 30)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.older_than_days))
