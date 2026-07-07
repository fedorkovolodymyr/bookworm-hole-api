from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.catalog import ContributorRole, ReleaseFormat


class CreateContributorSchema(BaseModel):
    full_name: str
    sort_name: str
    birth_year: int | None = None
    death_year: int | None = None
    bio: str | None = None


class UpdateContributorSchema(BaseModel):
    full_name: str | None = None
    sort_name: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    bio: str | None = None


class ContributorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    sort_name: str
    birth_year: int | None
    death_year: int | None
    bio: str | None
    slug: str
    created_at: datetime
    updated_at: datetime


class ContributorBookSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str


class ContributorReleaseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    format: ReleaseFormat
    publisher: str
    language: str


class ContributorDetailResponse(BaseModel):
    id: UUID
    full_name: str
    sort_name: str
    birth_year: int | None
    death_year: int | None
    bio: str | None
    slug: str
    created_at: datetime
    updated_at: datetime
    books_by_role: dict[ContributorRole, list[ContributorBookSummary]]
    releases_by_role: dict[ContributorRole, list[ContributorReleaseSummary]]


class AddContributorSchema(BaseModel):
    contributor_id: UUID
    role: ContributorRole
