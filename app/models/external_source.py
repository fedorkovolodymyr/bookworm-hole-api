import enum
from typing import Any

from sqlalchemy import Column, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class ExternalRefKind(str, enum.Enum):
    search = "search"
    isbn = "isbn"


class ExternalSourceRecord(SQLModel, IdMixin, TimestampMixin, table=True):
    __tablename__ = "external_source_records"
    __table_args__ = (
        Index(
            "ix_external_source_records_source_ref_kind_ref",
            "source",
            "ref_kind",
            "ref",
        ),
    )

    source: str = Field(max_length=64, index=True)
    ref_kind: ExternalRefKind = Field(
        sa_column=Column(SAEnum(ExternalRefKind), nullable=False)
    )
    ref: str = Field(max_length=255, index=True)
    payload: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
