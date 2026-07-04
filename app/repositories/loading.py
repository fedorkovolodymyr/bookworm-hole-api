from typing import Any

from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import LoaderOption


def eager(attr: Any) -> LoaderOption:
    # Any param sidesteps SQLModel relationship fields' pyright/selectinload type mismatch.
    return selectinload(attr)


def eager_nested(attr: Any, nested: Any) -> LoaderOption:
    return selectinload(attr).selectinload(nested)
