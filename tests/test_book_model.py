from sqlalchemy import Table, inspect

from app.models.books import Book
from app.models.contributor import BookContributor
from app.models.releases import Release


def test_book_table_columns():
    columns = inspect(Book).columns
    expected = {
        "id",
        "title",
        "original_title",
        "original_language",
        "first_publication_year",
        "description",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(columns.keys())
    assert columns["original_title"].nullable
    assert columns["original_language"].nullable
    assert columns["first_publication_year"].nullable


def test_book_defaults():
    book = Book(title="1984", description="Dystopian novel")
    assert book.original_title is None
    assert book.original_language is None
    assert book.first_publication_year is None


def test_book_releases_relationship():
    relationship = inspect(Book).relationships["releases"]
    assert relationship.mapper.class_ is Release
    assert relationship.back_populates == "book"


def test_book_contributors_relationship():
    relationship = inspect(Book).relationships["contributors"]
    secondary = relationship.secondary
    assert isinstance(secondary, Table)
    assert secondary.name == BookContributor.__tablename__
    assert relationship.back_populates == "books"
