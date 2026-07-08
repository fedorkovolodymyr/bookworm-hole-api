from typing import Any

from sqlalchemy import Table
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import LoaderOption


def eager(attr: Any) -> LoaderOption:
    # Any param sidesteps pyright/selectinload type mismatch on SQLModel fields.
    return selectinload(attr)


def eager_nested(attr: Any, nested: Any) -> LoaderOption:
    return selectinload(attr).selectinload(nested)


def table_of(model: Any) -> Table:
    # Any param sidesteps pyright's unknown typing of SQLModel's __table__.
    return model.__table__
