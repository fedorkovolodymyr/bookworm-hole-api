"""Contract tests for GoogleBooks adapter.

Verifies that the adapter produces expected normalized shape (ExternalBookDetail)
from recorded API responses (JSON fixtures).
"""

import json
from pathlib import Path

from app.models.catalog import ISBNKind, ReleaseFormat
from app.services.external.google_books import (
    _parse_contributors,
    _parse_cover_url,
    _parse_format,
    _parse_isbns,
    _parse_published_year,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "google_books"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


class TestGoogleBooksNormalization:
    """Test parsing functions that normalize GoogleBooks API responses."""

    def test_parse_published_year_extracts_year_from_date(self):
        assert _parse_published_year("1965") == 1965
        assert _parse_published_year("1965-06-01") == 1965
        assert _parse_published_year("2023") == 2023

    def test_parse_published_year_returns_none_for_missing(self):
        assert _parse_published_year(None) is None
        assert _parse_published_year("") is None
        assert _parse_published_year("unknown date") is None

    def test_parse_contributors_from_authors_list(self):
        authors = ["Frank Herbert"]
        contributors = _parse_contributors(authors)
        assert len(contributors) == 1
        assert contributors[0].full_name == "Frank Herbert"

    def test_parse_contributors_from_multiple_authors(self):
        authors = ["Author One", "Author Two", "Author Three"]
        contributors = _parse_contributors(authors)
        assert len(contributors) == 3
        assert [c.full_name for c in contributors] == authors

    def test_parse_contributors_returns_empty_list_for_missing(self):
        assert _parse_contributors(None) == []
        assert _parse_contributors([]) == []

    def test_parse_isbns_from_industry_identifiers(self):
        identifiers = [
            {"type": "ISBN_13", "identifier": "9780441013593"},
            {"type": "ISBN_10", "identifier": "0441013597"},
        ]
        isbns = _parse_isbns(identifiers)
        assert len(isbns) == 2
        isbn_13 = next(i for i in isbns if i.kind == ISBNKind.isbn13)
        isbn_10 = next(i for i in isbns if i.kind == ISBNKind.isbn10)
        assert isbn_13.code == "9780441013593"
        assert isbn_10.code == "0441013597"

    def test_parse_isbns_skips_unknown_types(self):
        identifiers = [
            {"type": "ISBN_13", "identifier": "9780441013593"},
            {"type": "UNKNOWN", "identifier": "12345"},
        ]
        isbns = _parse_isbns(identifiers)
        assert len(isbns) == 1
        assert isbns[0].kind == ISBNKind.isbn13

    def test_parse_isbns_returns_empty_list_for_missing(self):
        assert _parse_isbns(None) == []
        assert _parse_isbns([]) == []

    def test_parse_format_detects_ebook_from_epub(self):
        item = {
            "accessInfo": {
                "epub": {"isAvailable": True},
                "pdf": {"isAvailable": False},
            }
        }
        fmt = _parse_format(item)
        assert fmt == ReleaseFormat.ebook

    def test_parse_format_detects_ebook_from_pdf(self):
        item = {
            "accessInfo": {
                "epub": {"isAvailable": False},
                "pdf": {"isAvailable": True},
            }
        }
        fmt = _parse_format(item)
        assert fmt == ReleaseFormat.ebook

    def test_parse_format_detects_ebook_from_both(self):
        item = {
            "accessInfo": {
                "epub": {"isAvailable": True},
                "pdf": {"isAvailable": True},
            }
        }
        fmt = _parse_format(item)
        assert fmt == ReleaseFormat.ebook

    def test_parse_format_returns_other_for_non_ebook(self):
        item = {"accessInfo": {"epub": {"isAvailable": False}}}
        fmt = _parse_format(item)
        assert fmt == ReleaseFormat.other

    def test_parse_format_returns_other_for_missing_access_info(self):
        item = {}
        fmt = _parse_format(item)
        assert fmt == ReleaseFormat.other

    def test_parse_cover_url_from_thumbnail(self):
        volume_info = {
            "imageLinks": {
                "thumbnail": "http://books.google.com/books/content?id=test&img=1&zoom=1"
            }
        }
        url = _parse_cover_url(volume_info)
        assert url == "https://books.google.com/books/content?id=test&img=1&zoom=1"

    def test_parse_cover_url_from_small_thumbnail_fallback(self):
        volume_info = {
            "imageLinks": {
                "smallThumbnail": "http://books.google.com/books/content?id=test&img=1&zoom=5"
            }
        }
        url = _parse_cover_url(volume_info)
        assert url == "https://books.google.com/books/content?id=test&img=1&zoom=5"

    def test_parse_cover_url_prefers_thumbnail_over_small_thumbnail(self):
        volume_info = {
            "imageLinks": {
                "thumbnail": "http://books.google.com/books/content?id=test&img=1&zoom=1",
                "smallThumbnail": "http://books.google.com/books/content?id=test&img=1&zoom=5",
            }
        }
        url = _parse_cover_url(volume_info)
        assert "zoom=1" in url

    def test_parse_cover_url_returns_none_for_missing(self):
        assert _parse_cover_url({}) is None
        assert _parse_cover_url({"imageLinks": {}}) is None


class TestGoogleBooksFixtures:
    """Test that fixture data is correctly normalized."""

    def test_dune_isbn_fixture_is_valid(self):
        """Verify Dune ISBN fixture has expected structure."""
        fixture = _load_fixture("isbn_9780441013593.json")
        items = fixture.get("items", [])
        assert len(items) > 0
        assert items[0]["volumeInfo"]["title"] == "Dune"

    def test_dune_volume_fixture_is_valid(self):
        """Verify Dune volume fixture has expected structure."""
        fixture = _load_fixture("volume_abc123XYZ.json")
        assert fixture["id"] == "abc123XYZ"
        assert fixture["volumeInfo"]["title"] == "Dune"
        assert isinstance(fixture["volumeInfo"]["description"], str)
        assert "Arrakis" in fixture["volumeInfo"]["description"]

    def test_dune_search_fixture_is_valid(self):
        """Verify Dune search fixture has expected structure."""
        fixture = _load_fixture("search_dune.json")
        items = fixture.get("items", [])
        assert len(items) > 0
        assert items[0]["volumeInfo"]["title"] == "Dune"
