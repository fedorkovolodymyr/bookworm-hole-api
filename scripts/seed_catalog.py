import asyncio
import json
from pathlib import Path
from typing import Any, cast

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.db import async_session_factory
from app.models.catalog import (
    Book,
    Contributor,
    ContributorRole,
    ISBNKind,
    ReleaseFormat,
)
from app.repositories.import_repository import ImportRepository
from app.services.isbn import normalize_isbn


def _load_catalog_json() -> list[dict[str, Any]]:
    """Load catalog.json from disk."""
    catalog_path = Path(__file__).parent.parent / "seeds" / "catalog.json"
    with open(catalog_path) as f:
        data: Any = json.load(f)
        if not isinstance(data, list):
            msg = "Catalog must be a list"
            raise ValueError(msg)
        return cast(list[dict[str, Any]], data)


async def load_catalog(session: AsyncSession) -> None:
    """Load curated catalog from seeds/catalog.json, idempotent."""
    catalog = await asyncio.to_thread(_load_catalog_json)

    repo = ImportRepository(session)

    # Upsert contributors first
    contrib_map: dict[str, Contributor] = {}
    for book_data in catalog:
        contributors: list[Any] = cast(list[Any], book_data.get("contributors", []))
        for contrib_raw in contributors:
            contrib_dict = cast(dict[str, Any], contrib_raw)
            slug = cast(str, contrib_dict["slug"])
            if slug in contrib_map:
                continue

            result = await session.execute(
                select(Contributor).where(Contributor.slug == slug)
            )
            existing = result.scalars().first()
            if existing:
                contrib_map[slug] = existing
            else:
                new_contrib = Contributor(
                    full_name=cast(str, contrib_dict["full_name"]),
                    sort_name=cast(str, contrib_dict["sort_name"]),
                    slug=slug,
                    bio=cast(str | None, contrib_dict.get("bio")),
                )
                session.add(new_contrib)
                await session.flush()
                contrib_map[slug] = new_contrib

    logger.info(f"Contributors: {len(contrib_map)} upserted/loaded")

    # Process books
    for book_data in catalog:
        title = cast(str, book_data["title"])
        result = await session.execute(select(Book).where(Book.title == title))
        existing_book = result.scalars().first()
        if existing_book:
            book = existing_book
            logger.debug(f"Book '{title}' already exists")
        else:
            book = await repo.add_book(
                title=title,
                description=cast(str, book_data["description"]),
                first_publication_year=cast(
                    int | None, book_data.get("first_publication_year")
                ),
            )
            logger.debug(f"Created book '{title}'")

        # Link contributors to book
        contributors = cast(list[Any], book_data.get("contributors", []))
        for contrib_raw in contributors:
            contrib_dict = cast(dict[str, Any], contrib_raw)
            slug = cast(str, contrib_dict["slug"])
            contrib = contrib_map[slug]
            role = ContributorRole(cast(str, contrib_dict.get("role")))
            await repo.link_book_contributor(book.id, contrib.id, role)

        # Process releases for this book
        releases = cast(list[Any], book_data.get("releases", []))
        for release_data in releases:
            release_dict = cast(dict[str, Any], release_data)
            # Check if release exists (by format, language, publisher)
            existing_releases = [
                r
                for r in book.releases
                if r.format.value == release_dict["format"]
                and r.language == release_dict["language"]
                and r.publisher == release_dict["publisher"]
            ]
            if existing_releases:
                release = existing_releases[0]
                fmt = cast(str, release_dict["format"])
                lang = cast(str, release_dict["language"])
                logger.debug(f"Release '{title}' ({fmt}/{lang}) already exists")
            else:
                format_enum = ReleaseFormat(cast(str, release_dict["format"]))
                release = await repo.add_release(
                    book_id=book.id,
                    format=format_enum,
                    publisher=cast(str, release_dict["publisher"]),
                    published_year=cast(int | None, release_dict.get("published_year")),
                    language=cast(str, release_dict["language"]),
                )
                fmt = cast(str, release_dict["format"])
                lang = cast(str, release_dict["language"])
                logger.debug(f"Created release '{title}' ({fmt}/{lang})")

            # Link contributors to release
            contributors = cast(list[Any], book_data.get("contributors", []))
            for contrib_raw in contributors:
                contrib_dict = cast(dict[str, Any], contrib_raw)
                slug = cast(str, contrib_dict["slug"])
                contrib = contrib_map[slug]
                role = ContributorRole(cast(str, contrib_dict.get("role")))
                await repo.link_release_contributor(release.id, contrib.id, role)

            # Process ISBNs for this release
            isbns = cast(list[Any], release_dict.get("isbns", []))
            for isbn_raw in isbns:
                isbn_dict = cast(dict[str, Any], isbn_raw)
                code = cast(str, isbn_dict["code"])

                # Check if ISBN already exists in this release
                existing_isbns = [i for i in release.isbns if i.code_original == code]
                if existing_isbns:
                    logger.debug(f"ISBN {code} already in release")
                    continue

                # Normalize ISBN-10 to ISBN-13, handle errors gracefully
                kind = ISBNKind(cast(str, isbn_dict.get("kind", "other")))
                if kind in (ISBNKind.isbn10, ISBNKind.isbn13):
                    try:
                        normalized = normalize_isbn(code)
                        await repo.add_isbn(
                            release_id=release.id,
                            code_normalized=normalized,
                            code_original=code,
                            kind=kind,
                        )
                        logger.debug(f"Added ISBN {code} → {normalized}")
                    except ValueError as e:
                        logger.warning(f"Invalid ISBN {code}: {e}")
                else:
                    # For non-ISBN codes (ASIN, etc.), store as-is
                    await repo.add_isbn(
                        release_id=release.id,
                        code_normalized=code,
                        code_original=code,
                        kind=kind,
                    )
                    logger.debug(f"Added {kind.value} {code}")

    await session.commit()
    logger.info("Catalog seed data loaded successfully")


async def main() -> None:
    async with async_session_factory() as session:
        await load_catalog(session)


if __name__ == "__main__":
    asyncio.run(main())
