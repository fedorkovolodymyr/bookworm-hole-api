import json
from pathlib import Path

import pytest


class TestCatalogStructure:
    """Test seeds/catalog.json structure and content."""

    @pytest.fixture
    def catalog(self) -> list[dict]:
        """Load catalog.json."""
        path = Path(__file__).parent.parent / "seeds" / "catalog.json"
        with open(path) as f:
            return json.load(f)

    def test_catalog_is_list(self, catalog: list[dict]) -> None:
        assert isinstance(catalog, list)
        assert len(catalog) > 0

    def test_minimum_book_count(self, catalog: list[dict]) -> None:
        """At least 36 books as per this implementation."""
        assert len(catalog) >= 36

    def test_each_book_has_required_fields(self, catalog: list[dict]) -> None:
        required = {"title", "description", "contributors", "releases"}
        for book in catalog:
            title = book.get("title")
            assert required.issubset(book.keys()), f"Missing fields in {title}"

    def test_each_book_has_multiple_releases(self, catalog: list[dict]) -> None:
        """At least 36 books should have 2+ releases (dedup test)."""
        multi_release_count = sum(1 for b in catalog if len(b.get("releases", [])) >= 2)
        msg = f"Only {multi_release_count} books with 2+ releases"
        assert multi_release_count >= 36, msg

    def test_each_release_has_required_fields(self, catalog: list[dict]) -> None:
        required = {"format", "publisher", "language", "isbns"}
        for book in catalog:
            for release in book.get("releases", []):
                title = book.get("title")
                assert required.issubset(release.keys()), (
                    f"Missing fields in release for {title}"
                )

    def test_each_contributor_has_required_fields(self, catalog: list[dict]) -> None:
        required = {"full_name", "sort_name", "slug", "role"}
        for book in catalog:
            for contrib in book.get("contributors", []):
                title = book.get("title")
                assert required.issubset(contrib.keys()), (
                    f"Missing contributor fields in {title}"
                )

    def test_contributors_have_valid_roles(self, catalog: list[dict]) -> None:
        valid_roles = {
            "author",
            "co_author",
            "translator",
            "illustrator",
            "editor",
            "narrator",
            "foreword",
            "other",
        }
        for book in catalog:
            for contrib in book.get("contributors", []):
                role = contrib.get("role")
                name = contrib.get("full_name")
                assert role in valid_roles, f"Invalid role {role} for {name}"

    def test_releases_have_valid_formats(self, catalog: list[dict]) -> None:
        valid_formats = {"hardcover", "paperback", "ebook", "audiobook", "other"}
        for book in catalog:
            for release in book.get("releases", []):
                fmt = release.get("format")
                title = book.get("title")
                assert fmt in valid_formats, f"Invalid format {fmt} in {title}"

    def test_each_release_has_at_least_one_isbn(self, catalog: list[dict]) -> None:
        for book in catalog:
            for release in book.get("releases", []):
                isbns = release.get("isbns", [])
                title = book.get("title")
                assert len(isbns) > 0, f"Release has no ISBNs in {title}"

    def test_isbn_kinds_are_valid(self, catalog: list[dict]) -> None:
        valid_kinds = {"isbn10", "isbn13", "asin", "other"}
        for book in catalog:
            for release in book.get("releases", []):
                for isbn in release.get("isbns", []):
                    kind = isbn.get("kind")
                    title = book.get("title")
                    assert kind in valid_kinds, f"Invalid ISBN kind {kind} in {title}"

    def test_isbn_codes_are_strings(self, catalog: list[dict]) -> None:
        for book in catalog:
            for release in book.get("releases", []):
                for isbn in release.get("isbns", []):
                    code = isbn.get("code")
                    title = book.get("title")
                    assert isinstance(code, str), f"ISBN code not string in {title}"

    def test_at_least_one_book_has_multiple_isbns_per_release(
        self, catalog: list[dict]
    ) -> None:
        """At least one release should have both ISBN-10 and ISBN-13."""
        found = False
        for book in catalog:
            for release in book.get("releases", []):
                isbns = release.get("isbns", [])
                if len(isbns) >= 2:
                    kinds = [i.get("kind") for i in isbns]
                    if "isbn10" in kinds and "isbn13" in kinds:
                        found = True
                        break
            if found:
                break
        assert found, "No release with both ISBN-10 and ISBN-13 found"

    def test_isbn_format_compliance(self, catalog: list[dict]) -> None:
        """ISBNs should have correct format."""
        for book in catalog:
            for release in book.get("releases", []):
                for isbn in release.get("isbns", []):
                    code = isbn.get("code", "")
                    kind = isbn.get("kind", "")
                    if kind == "isbn10":
                        # ISBN-10: 10 digits, possibly with hyphens
                        digits = code.replace("-", "")
                        assert len(digits) == 10 and digits.isdigit(), (
                            f"Invalid ISBN-10 format: {code}"
                        )
                    elif kind == "isbn13":
                        # ISBN-13: 13 digits, possibly with hyphens
                        digits = code.replace("-", "")
                        assert len(digits) == 13 and digits.isdigit(), (
                            f"Invalid ISBN-13 format: {code}"
                        )
