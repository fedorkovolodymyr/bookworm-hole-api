from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.catalog import ISBN, Book
from app.models.contribution import Contribution, ContributionKind
from app.services.isbn import normalize_isbn

_REQUIRED_FIELDS_BY_KIND: dict[ContributionKind, tuple[str, ...]] = {
    ContributionKind.new_book: ("title", "description"),
    ContributionKind.new_release: ("format", "publisher", "language"),
    ContributionKind.new_contributor: ("full_name", "sort_name", "slug"),
}


@dataclass
class RuleResult:
    passed: bool
    message: str | None = None


class Rule(ABC):
    @abstractmethod
    async def check(self, contribution: Contribution) -> RuleResult: ...


class MissingRequiredFieldsRule(Rule):
    """Flags a contribution when its payload is missing fields required for its kind."""

    async def check(self, contribution: Contribution) -> RuleResult:
        required = _REQUIRED_FIELDS_BY_KIND.get(contribution.kind, ())
        missing = [field for field in required if not contribution.payload.get(field)]
        if missing:
            return RuleResult(
                passed=False,
                message=f"Missing required fields: {', '.join(missing)}",
            )
        return RuleResult(passed=True)


class ISBNAlreadyExistsRule(Rule):
    """Flags a new-release contribution whose ISBN already exists in the catalog."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def check(self, contribution: Contribution) -> RuleResult:
        if contribution.kind != ContributionKind.new_release:
            return RuleResult(passed=True)
        raw_isbn = contribution.payload.get("isbn")
        if not raw_isbn:
            return RuleResult(passed=True)
        try:
            normalized = normalize_isbn(raw_isbn)
        except ValueError:
            return RuleResult(passed=True)
        exists = await self.session.execute(
            select(col(ISBN.id)).where(col(ISBN.code_normalized) == normalized)
        )
        if exists.first() is not None:
            return RuleResult(
                passed=False, message=f"ISBN {raw_isbn} already exists in the catalog"
            )
        return RuleResult(passed=True)


class DuplicateTitleAuthorRule(Rule):
    """Flags a new-book contribution whose title already exists (case-insensitive)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def check(self, contribution: Contribution) -> RuleResult:
        if contribution.kind != ContributionKind.new_book:
            return RuleResult(passed=True)
        title = contribution.payload.get("title")
        if not title:
            return RuleResult(passed=True)
        exists = await self.session.execute(
            select(col(Book.id)).where(func.lower(col(Book.title)) == title.lower())
        )
        if exists.first() is not None:
            return RuleResult(
                passed=False, message=f"A book titled {title!r} may already exist"
            )
        return RuleResult(passed=True)


def default_rules(session: AsyncSession) -> list[Rule]:
    return [
        MissingRequiredFieldsRule(),
        ISBNAlreadyExistsRule(session),
        DuplicateTitleAuthorRule(session),
    ]


async def run_rules(contribution: Contribution, rules: list[Rule]) -> list[str]:
    warnings: list[str] = []
    for rule in rules:
        result = await rule.check(contribution)
        if not result.passed and result.message:
            warnings.append(result.message)
    return warnings
