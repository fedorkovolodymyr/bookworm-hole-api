from sqlalchemy import Index, inspect

from app.models.reading_session import PositionUnit, ReadingSession


def test_reading_session_table_columns():
    columns = inspect(ReadingSession).columns
    expected = {
        "id",
        "user_id",
        "release_id",
        "started_at",
        "ended_at",
        "pages_read",
        "position_start",
        "position_end",
        "position_unit",
        "notes",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(columns.keys())
    assert not columns["user_id"].nullable
    assert not columns["release_id"].nullable
    assert not columns["started_at"].nullable
    assert columns["ended_at"].nullable
    assert columns["pages_read"].nullable
    assert columns["position_start"].nullable
    assert columns["position_end"].nullable
    assert columns["position_unit"].nullable
    assert columns["notes"].nullable


def test_position_unit_values():
    assert {unit.value for unit in PositionUnit} == {
        "page",
        "percent",
        "location",
        "timestamp",
    }


def test_reading_session_active_partial_unique_index():
    indexes = [i for i in ReadingSession.__table__.indexes if isinstance(i, Index)]
    active_index = next(
        (i for i in indexes if i.name == "uq_reading_session_active_user_release"),
        None,
    )
    assert active_index is not None
    assert active_index.unique
    assert {c.name for c in active_index.columns} == {"user_id", "release_id"}
