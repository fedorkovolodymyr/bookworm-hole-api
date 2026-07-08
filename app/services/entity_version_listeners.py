from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import event, func, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapper

from app.core.audit_context import (
    current_change_source,
    current_changed_by_user_id,
    current_contribution_id,
)
from app.models.catalog import Book, Contributor, Release
from app.models.entity_version import EntityType, EntityVersion
from app.repositories.loading import table_of

_TRACKED_MODELS: dict[type, EntityType] = {
    Book: EntityType.book,
    Release: EntityType.release,
    Contributor: EntityType.contributor,
}

_versions_table = table_of(EntityVersion)

ModelListener = Callable[[Mapper[Any], Connection, Any], None]


def _record_snapshot(
    connection: Connection, entity_type: EntityType, target: Any
) -> None:
    max_version = connection.execute(
        select(func.coalesce(func.max(_versions_table.c.version_number), 0)).where(
            _versions_table.c.entity_type == entity_type,
            _versions_table.c.entity_id == target.id,
        )
    ).scalar_one()
    snapshot = target.model_dump(mode="json")
    connection.execute(
        _versions_table.insert().values(
            entity_type=entity_type,
            entity_id=target.id,
            version_number=max_version + 1,
            snapshot=snapshot,
            changed_by_user_id=current_changed_by_user_id(),
            change_source=current_change_source(),
            contribution_id=current_contribution_id(),
            created_at=datetime.now(UTC),
        )
    )


def _make_listener(entity_type: EntityType) -> ModelListener:
    def _listener(_mapper: Mapper[Any], connection: Connection, target: Any) -> None:
        _record_snapshot(connection, entity_type, target)

    return _listener


def register_listeners() -> None:
    """Register after_insert/after_update snapshot listeners for tracked models.

    Idempotent-ish per process: called once at app startup (see `app/main.py`).
    Snapshots are written on the raw DB connection inside the same flush that
    triggered them, so they can't get out of sync with the mutation.
    """
    for model, entity_type in _TRACKED_MODELS.items():
        listener = _make_listener(entity_type)
        event.listen(model, "after_insert", listener)
        event.listen(model, "after_update", listener)
