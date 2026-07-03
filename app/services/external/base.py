from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.models.catalog import ContributorRole, ISBNKind, ReleaseFormat


@dataclass(frozen=True)
class ExternalContributor:
    full_name: str
    role: ContributorRole = ContributorRole.author


@dataclass(frozen=True)
class ExternalISBN:
    code: str
    kind: ISBNKind


@dataclass(frozen=True)
class ExternalBookHit:
    title: str
    contributors: list[ExternalContributor]
    isbns: list[ExternalISBN]
    cover_image_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalBookDetail:
    title: str
    description: str | None
    contributors: list[ExternalContributor]
    isbns: list[ExternalISBN]
    format: ReleaseFormat
    publisher: str | None
    published_year: int | None
    language: str | None
    cover_image_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class BookSourceAdapter(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str) -> list[ExternalBookHit]: ...

    @abstractmethod
    async def get_by_isbn(self, isbn: str) -> ExternalBookDetail | None: ...
