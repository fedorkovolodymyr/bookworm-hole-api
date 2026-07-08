from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import UUID

from app.models.entity_version import ChangeSource

_change_source_ctx_var: ContextVar[ChangeSource] = ContextVar(
    "change_source", default=ChangeSource.system
)
_changed_by_user_id_ctx_var: ContextVar[UUID | None] = ContextVar(
    "changed_by_user_id", default=None
)
_contribution_id_ctx_var: ContextVar[UUID | None] = ContextVar(
    "contribution_id", default=None
)


@contextmanager
def audit_as(
    change_source: ChangeSource,
    changed_by_user_id: UUID | None = None,
    contribution_id: UUID | None = None,
) -> Iterator[None]:
    """Attribute Book/Release/Contributor mutations within this block to a source.

    Read by the version-snapshot event listeners in
    `app/services/entity_version_listeners.py`. Defaults to `ChangeSource.system`
    with no user/contribution when not set (e.g. background jobs).
    """
    source_token = _change_source_ctx_var.set(change_source)
    user_token = _changed_by_user_id_ctx_var.set(changed_by_user_id)
    contribution_token = _contribution_id_ctx_var.set(contribution_id)
    try:
        yield
    finally:
        _change_source_ctx_var.reset(source_token)
        _changed_by_user_id_ctx_var.reset(user_token)
        _contribution_id_ctx_var.reset(contribution_token)


def current_change_source() -> ChangeSource:
    return _change_source_ctx_var.get()


def current_changed_by_user_id() -> UUID | None:
    return _changed_by_user_id_ctx_var.get()


def current_contribution_id() -> UUID | None:
    return _contribution_id_ctx_var.get()
