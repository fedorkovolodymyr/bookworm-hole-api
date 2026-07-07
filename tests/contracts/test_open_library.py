"""Contract tests for OpenLibrary adapter.

Verifies that the adapter produces expected normalized shape (ExternalBookDetail)
from recorded API responses (JSON fixtures).
"""

import json
from pathlib import Path

from app.models.catalog import ISBNKind, ReleaseFormat
from app.services.external.open_library import (
    _parse_contributors,
    _parse_cover_url,
    _parse_description,
    _parse_format,
    _parse_isbns,
    _parse_language,
    _parse_published_year,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "open_library"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


class TestOpenLibraryNormalization:
    """Test parsing functions that normalize OpenLibrary API responses."""

    def test_parse_format_from_physical_format(self):
        assert _parse_format("hardcover") == ReleaseFormat.hardcover
        assert _parse_format("paperback") == ReleaseFormat.paperback
        assert _parse_format("ebook") == ReleaseFormat.ebook
        assert _parse_format("audiobook") == ReleaseFormat.audiobook
        assert _parse_format("unknown") == ReleaseFormat.other
        assert _parse_format(None) == ReleaseFormat.other

    def test_parse_format_case_insensitive(self):
        assert _parse_format("Paperback") == ReleaseFormat.paperback
        assert _parse_format("HARDCOVER") == ReleaseFormat.hardcover

    def test_parse_format_with_whitespace(self):
        assert _parse_format("  paperback  ") == ReleaseFormat.paperback

    def test_parse_published_year_extracts_year_from_date(self):
        assert _parse_published_year("1965") == 1965
        assert _parse_published_year("2023-06-15") == 2023
        assert _parse_published_year("June 1, 1965") == 1965

    def test_parse_published_year_returns_none_for_missing(self):
        assert _parse_published_year(None) is None
        assert _parse_published_year("") is None
        assert _parse_published_year("no year here") is None

    def test_parse_language_from_language_list(self):
        languages = [{"key": "/languages/eng"}]
        assert _parse_language(languages) == "eng"

    def test_parse_language_returns_none_for_missing(self):
        assert _parse_language(None) is None
        assert _parse_language([]) is None
        assert _parse_language([{"key": ""}]) is None

    def test_parse_cover_url_from_covers_array(self):
        covers = [8314396]
        url = _parse_cover_url(covers)
        assert url == "https://covers.openlibrary.org/b/id/8314396-L.jpg"

    def test_parse_cover_url_returns_none_for_missing(self):
        assert _parse_cover_url(None) is None
        assert _parse_cover_url([]) is None

    def test_parse_description_from_dict(self):
        work_doc = {
            "description": {
                "type": "/type/text",
                "value": "A great book about desert planets.",
            }
        }
        desc = _parse_description(work_doc)
        assert desc == "A great book about desert planets."

    def test_parse_description_from_string(self):
        work_doc = {"description": "A great book about desert planets."}
        desc = _parse_description(work_doc)
        assert desc == "A great book about desert planets."

    def test_parse_description_returns_none_for_missing(self):
        assert _parse_description({}) is None
        assert _parse_description({"description": None}) is None
        assert _parse_description({"description": []}) is None

    def test_parse_contributors_from_by_statement(self):
        isbn_doc = {"by_statement": "Frank Herbert"}
        contributors = _parse_contributors(isbn_doc)
        assert len(contributors) == 1
        assert contributors[0].full_name == "Frank Herbert"

    def test_parse_contributors_returns_empty_list_for_missing(self):
        assert _parse_contributors({}) == []
        assert _parse_contributors({"by_statement": ""}) == []
        assert _parse_contributors({"by_statement": None}) == []

    def test_parse_isbns_from_isbn_lists(self):
        isbn_doc = {
            "isbn_13": ["9780441013593"],
            "isbn_10": ["0441013597"],
        }
        isbns = _parse_isbns(isbn_doc)
        assert len(isbns) == 2
        isbn_13 = next(i for i in isbns if i.kind == ISBNKind.isbn13)
        isbn_10 = next(i for i in isbns if i.kind == ISBNKind.isbn10)
        assert isbn_13.code == "9780441013593"
        assert isbn_10.code == "0441013597"

    def test_parse_isbns_returns_empty_list_for_missing(self):
        assert _parse_isbns({}) == []
        assert _parse_isbns({"isbn_13": [], "isbn_10": []}) == []


class TestOpenLibraryFixtures:
    """Test that fixture data is correctly normalized."""

    def test_dune_isbn_fixture_is_valid(self):
        """Verify Dune ISBN fixture has expected structure."""
        fixture = _load_fixture("isbn_9780441013593.json")
        assert fixture["title"] == "Dune"
        assert "9780441013593" in fixture["isbn_13"]
        assert fixture["physical_format"] == "Paperback"

    def test_dune_work_fixture_is_valid(self):
        """Verify Dune work fixture has expected structure."""
        fixture = _load_fixture("work_OL893415W.json")
        assert fixture["title"] == "Dune"
        assert isinstance(fixture["description"], dict)
        assert "Arrakis" in fixture["description"]["value"]

    def test_dune_search_fixture_is_valid(self):
        """Verify Dune search fixture has expected structure."""
        fixture = _load_fixture("search_dune.json")
        docs = fixture.get("docs", [])
        assert len(docs) > 0
        assert docs[0]["title"] == "Dune"
