from typing import Any

from sqlalchemy.orm import selectinload
from sqlalchemy.orm.strategy_options import _AbstractLoad


def eager(attr: Any) -> _AbstractLoad:
    # Any param sidesteps SQLModel relationship fields' pyright/selectinload type mismatch.
    return selectinload(attr)


def eager_nested(attr: Any, nested: Any) -> _AbstractLoad:
    return selectinload(attr).selectinload(nested)
