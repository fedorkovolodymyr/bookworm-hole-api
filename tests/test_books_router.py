from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, delete

from app.core.db import async_engine, get_session
from app.main import app
from app.models.catalog import ISBN, ISBNKind, Release, ReleaseFormat
from app.models.catalog import Book as BookModel


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def book_with_releases():
    try:
        async for session in get_session():
            book = BookModel(title="Dune", description="Desert planet epic")
            session.add(book)
            await session.flush()

            hardcover = Release(
                book_id=book.id,
                format=ReleaseFormat.hardcover,
                publisher="Chilton Books",
                language="en",
            )
            paperback = Release(
                book_id=book.id,
                format=ReleaseFormat.paperback,
                publisher="Ace Books",
                language="en",
            )
            session.add(hardcover)
            session.add(paperback)
            await session.flush()

            hardcover_isbn = ISBN(
                release_id=hardcover.id,
                code_normalized="9780441013593",
                code_original="0441013597",
                kind=ISBNKind.isbn13,
                created_at=datetime.now(UTC),
            )
            paperback_isbn = ISBN(
                release_id=paperback.id,
                code_normalized="9780143111580",
                code_original="9780143111580",
                kind=ISBNKind.isbn13,
                created_at=datetime.now(UTC),
            )
            session.add(hardcover_isbn)
            session.add(paperback_isbn)
            await session.commit()

            yield book, hardcover_isbn, paperback_isbn

            await session.execute(
                delete(ISBN).where(
                    col(ISBN.release_id).in_([hardcover.id, paperback.id])
                )
            )
            await session.execute(
                delete(Release).where(col(Release.id).in_([hardcover.id, paperback.id]))
            )
            await session.execute(delete(BookModel).where(col(BookModel.id) == book.id))
            await session.commit()
    except (SQLAlchemyError, OSError) as exc:
        pytest.skip(f"database unavailable: {exc}")
    finally:
        await async_engine.dispose()


async def test_retrieve_book_by_isbn_dedup_and_shape(
    client: AsyncClient, book_with_releases
):
    book, hardcover_isbn, paperback_isbn = book_with_releases

    response_hc = await client.get(
        f"/api/v1/books/by-isbn/{hardcover_isbn.code_original}"
    )
    response_pb = await client.get(
        f"/api/v1/books/by-isbn/{paperback_isbn.code_original}"
    )

    assert response_hc.status_code == 200
    assert response_pb.status_code == 200
    data = response_hc.json()
    assert data["id"] == str(book.id)
    assert response_pb.json()["id"] == str(book.id)
    assert len(data["releases"]) == 2
    assert all(len(release["isbns"]) == 1 for release in data["releases"])


async def test_retrieve_book_by_isbn_not_found(client: AsyncClient):
    response = await client.get("/api/v1/books/by-isbn/9999999999999")
    assert response.status_code == 404


async def test_retrieve_book_by_isbn_invalid_input(client: AsyncClient):
    response = await client.get("/api/v1/books/by-isbn/not-an-isbn")
    assert response.status_code == 404
