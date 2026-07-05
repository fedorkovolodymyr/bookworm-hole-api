from __future__ import annotations

import sys
from contextvars import ContextVar
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from loguru import Record

request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def _inject_request_id(record: Record) -> None:
    record["extra"].setdefault("request_id", request_id_ctx_var.get())


def configure_logging(log_level: str) -> int:
    """Configure loguru to emit JSON logs with the current request ID attached."""
    logger.configure(patcher=_inject_request_id)
    return logger.add(sys.stderr, level=log_level, serialize=True)
