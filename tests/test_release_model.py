from sqlalchemy import inspect

from app.models.catalog import Book, Release


def test_release_table_columns():
    columns = inspect(Release).columns
    expected = {"id", "isbn", "book_id", "created_at", "updated_at"}
    assert expected.issubset(columns.keys())
    assert columns["isbn"].unique
    assert not columns["book_id"].nullable


def test_release_book_relationship():
    relationship = inspect(Release).relationships["book"]
    assert relationship.mapper.class_ is Book
    assert relationship.back_populates == "releases"
