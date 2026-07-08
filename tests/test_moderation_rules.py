import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import ISBN, Book, ISBNKind, Release, ReleaseFormat
from app.models.contribution import Contribution, ContributionKind, ContributionStatus
from app.services.moderation.rules import (
    DuplicateTitleAuthorRule,
    ISBNAlreadyExistsRule,
    MissingRequiredFieldsRule,
    default_rules,
    run_rules,
)

VALID_ISBN13 = "9780441013593"


def _contribution(kind: ContributionKind, payload: dict[str, object]) -> Contribution:
    from uuid import uuid4

    return Contribution(
        user_id=uuid4(),
        kind=kind,
        target_id=None,
        payload=payload,
        status=ContributionStatus.submitted,
    )


class TestMissingRequiredFieldsRule:
    async def test_passes_when_all_required_fields_present(self):
        rule = MissingRequiredFieldsRule()
        contribution = _contribution(
            ContributionKind.new_book,
            {"title": "Dune", "description": "Desert planet epic"},
        )
        result = await rule.check(contribution)
        assert result.passed

    async def test_flags_missing_required_fields(self):
        rule = MissingRequiredFieldsRule()
        contribution = _contribution(ContributionKind.new_book, {"title": "Dune"})
        result = await rule.check(contribution)
        assert not result.passed
        assert result.message is not None
        assert "description" in result.message

    async def test_passes_for_kind_with_no_required_fields(self):
        rule = MissingRequiredFieldsRule()
        contribution = _contribution(ContributionKind.edit_book, {})
        result = await rule.check(contribution)
        assert result.passed


class TestISBNAlreadyExistsRule:
    async def test_ignores_non_new_release_contributions(
        self, db_session: AsyncSession
    ):
        rule = ISBNAlreadyExistsRule(db_session)
        contribution = _contribution(ContributionKind.new_book, {"isbn": VALID_ISBN13})
        result = await rule.check(contribution)
        assert result.passed

    async def test_passes_when_isbn_not_in_catalog(self, db_session: AsyncSession):
        rule = ISBNAlreadyExistsRule(db_session)
        contribution = _contribution(
            ContributionKind.new_release, {"isbn": VALID_ISBN13}
        )
        result = await rule.check(contribution)
        assert result.passed

    async def test_flags_isbn_already_in_catalog(self, db_session: AsyncSession):
        book = Book(title="Dune", description="Desert planet epic")
        db_session.add(book)
        await db_session.flush()
        release = Release(
            book_id=book.id,
            format=ReleaseFormat.hardcover,
            publisher="Chilton Books",
            language="en",
        )
        db_session.add(release)
        await db_session.flush()
        db_session.add(
            ISBN(
                release_id=release.id,
                code_normalized=VALID_ISBN13,
                code_original=VALID_ISBN13,
                kind=ISBNKind.isbn13,
            )
        )
        await db_session.flush()

        rule = ISBNAlreadyExistsRule(db_session)
        contribution = _contribution(
            ContributionKind.new_release, {"isbn": VALID_ISBN13}
        )
        result = await rule.check(contribution)
        assert not result.passed
        assert result.message is not None
        assert VALID_ISBN13 in result.message


class TestDuplicateTitleAuthorRule:
    async def test_ignores_non_new_book_contributions(self, db_session: AsyncSession):
        rule = DuplicateTitleAuthorRule(db_session)
        contribution = _contribution(ContributionKind.edit_book, {"title": "Dune"})
        result = await rule.check(contribution)
        assert result.passed

    async def test_passes_when_title_not_in_catalog(self, db_session: AsyncSession):
        rule = DuplicateTitleAuthorRule(db_session)
        contribution = _contribution(ContributionKind.new_book, {"title": "Dune"})
        result = await rule.check(contribution)
        assert result.passed

    async def test_flags_duplicate_title(self, db_session: AsyncSession):
        db_session.add(Book(title="Dune", description="Desert planet epic"))
        await db_session.flush()

        rule = DuplicateTitleAuthorRule(db_session)
        contribution = _contribution(ContributionKind.new_book, {"title": "dune"})
        result = await rule.check(contribution)
        assert not result.passed
        assert result.message is not None
        assert "dune" in result.message


class TestRunRules:
    async def test_collects_warnings_from_failing_rules_only(
        self, db_session: AsyncSession
    ):
        contribution = _contribution(ContributionKind.new_book, {})
        warnings = await run_rules(contribution, default_rules(db_session))
        assert len(warnings) == 1
        assert "title" in warnings[0]


@pytest.fixture
async def submitted_contribution(db_session: AsyncSession) -> Contribution:
    from uuid import uuid4

    contribution = Contribution(
        user_id=uuid4(),
        kind=ContributionKind.new_book,
        target_id=None,
        payload={"title": "Dune"},
        status=ContributionStatus.submitted,
    )
    db_session.add(contribution)
    await db_session.flush()
    await db_session.refresh(contribution)
    return contribution


class TestAdminQueueIncludesWarnings:
    async def test_list_includes_warnings_for_incomplete_payload(
        self, admin_client, submitted_contribution: Contribution
    ):
        response = await admin_client.get(
            "/api/v1/admin/contributions?status=submitted"
        )
        assert response.status_code == 200
        data = response.json()
        item = next(
            item
            for item in data["items"]
            if item["id"] == str(submitted_contribution.id)
        )
        assert item["warnings"]
        assert "description" in item["warnings"][0]

    async def test_diff_includes_warnings_for_incomplete_payload(
        self, admin_client, submitted_contribution: Contribution
    ):
        response = await admin_client.get(
            f"/api/v1/admin/contributions/{submitted_contribution.id}/diff"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["warnings"]
        assert "description" in data["warnings"][0]
