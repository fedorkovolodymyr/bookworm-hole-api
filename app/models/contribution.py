import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class ContributionKind(str, enum.Enum):
    new_book = "new_book"
    new_release = "new_release"
    new_contributor = "new_contributor"
    edit_book = "edit_book"
    edit_release = "edit_release"
    edit_contributor = "edit_contributor"


class ContributionStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"
    merged = "merged"


class Contribution(SQLModel, IdMixin, TimestampMixin, table=True):
    """A user-submitted proposal to add or edit a catalog entity.

    `payload` holds the full proposed state as JSON (versioned via a
    `schema_version` key so future changes to its shape stay backward
    compatible). The merge that applies an approved payload to the target
    entity (or creates a new one) is handled by a separate service — this
    model only stores the submission and its review lifecycle.
    """

    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    kind: ContributionKind = Field(
        sa_column=Column(SAEnum(ContributionKind), nullable=False)
    )
    # No FK constraint: the referenced table depends on `kind` (book, release,
    # or contributor), so this is a loose UUID rather than a real relationship.
    target_id: uuid.UUID | None = Field(default=None, index=True)
    payload: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    status: ContributionStatus = Field(
        default=ContributionStatus.draft,
        sa_column=Column(
            SAEnum(ContributionStatus),
            nullable=False,
            default=ContributionStatus.draft,
        ),
    )
    reviewer_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True
    )
    review_notes: str | None = Field(default=None)
    decided_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
