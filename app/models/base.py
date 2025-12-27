from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, declarative_mixin
from sqlalchemy.sql import func

Base = declarative_base()


@declarative_mixin
class IdMixin:
    id = Column(UUID(as_uuid=True), primary_key=True, default=func.uuid_generate_v4())
