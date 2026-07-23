from typing import Any

from loguru import logger

from app.core.db import async_session_factory
from app.services.catalog_import_profiles import CATALOG_IMPORT_PROFILES
from app.services.catalog_import_service import CatalogImportService


class UnknownCatalogImportProfileError(ValueError):
    def __init__(self, profile_name: str) -> None:
        super().__init__(f"Unknown catalog import profile: {profile_name}")


async def import_catalog_profile(
    ctx: dict[str, Any], profile_name: str
) -> dict[str, int]:
    profile = CATALOG_IMPORT_PROFILES.get(profile_name)
    if profile is None:
        raise UnknownCatalogImportProfileError(profile_name)

    async with async_session_factory() as session:
        summary = await CatalogImportService(session).run_profile(profile)
        await session.commit()

    logger.info(
        f"Catalog import profile '{profile_name}' done: "
        f"imported={summary.imported} attempted={summary.attempted} "
        f"failed={summary.failed}"
    )
    return {
        "imported": summary.imported,
        "attempted": summary.attempted,
        "failed": summary.failed,
        "target_count": summary.target_count,
    }
