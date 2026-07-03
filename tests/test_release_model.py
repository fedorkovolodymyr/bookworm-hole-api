from sqlalchemy import Table, inspect

from app.models.catalog import ISBN, Book, Contributor, Release, ReleaseContributor


def test_release_table_columns():
    columns = inspect(Release).columns
    expected = {
        "id",
        "book_id",
        "format",
        "publisher",
        "published_year",
        "language",
        "page_count",
        "duration_minutes",
        "cover_image_url",
        "description_override",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(columns.keys())
    assert not columns["book_id"].nullable
    assert not columns["format"].nullable
    assert columns["page_count"].nullable
    assert columns["duration_minutes"].nullable
    assert columns["description_override"].nullable


def test_release_book_relationship():
    relationship = inspect(Release).relationships["book"]
    assert relationship.mapper.class_ is Book
    assert relationship.back_populates == "releases"


def test_release_isbns_relationship():
    relationship = inspect(Release).relationships["isbns"]
    assert relationship.mapper.class_ is ISBN
    assert relationship.back_populates == "release"


def test_release_contributors_relationship():
    relationship = inspect(Release).relationships["contributors"]
    secondary = relationship.secondary
    assert isinstance(secondary, Table)
    assert secondary.name == ReleaseContributor.__tablename__
    assert relationship.back_populates == "releases"


def test_isbn_table_columns():
    columns = inspect(ISBN).columns
    expected = {
        "id",
        "release_id",
        "code_normalized",
        "code_original",
        "kind",
        "created_at",
    }
    assert expected.issubset(columns.keys())
    assert columns["code_normalized"].unique
    assert not columns["release_id"].nullable


def test_isbn_release_relationship():
    relationship = inspect(ISBN).relationships["release"]
    assert relationship.mapper.class_ is Release
    assert relationship.back_populates == "isbns"


def test_contributor_releases_relationship():
    relationship = inspect(Contributor).relationships["releases"]
    secondary = relationship.secondary
    assert isinstance(secondary, Table)
    assert secondary.name == ReleaseContributor.__tablename__
    assert relationship.back_populates == "contributors"
