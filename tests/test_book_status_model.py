from sqlalchemy import CheckConstraint, Index, inspect

from app.models.book_status import BookStatus, BookStatusKind


def test_book_status_table_columns():
    columns = inspect(BookStatus).columns
    expected = {
        "id",
        "user_id",
        "book_id",
        "release_id",
        "status",
        "acquired_at",
        "notes",
        "lent_to_user_id",
        "lent_to_name",
        "lent_at",
        "returned_at",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(columns.keys())
    assert columns["book_id"].nullable
    assert columns["release_id"].nullable
    assert columns["acquired_at"].nullable
    assert columns["lent_to_user_id"].nullable
    assert columns["lent_to_name"].nullable


def test_book_status_kind_values():
    assert {kind.value for kind in BookStatusKind} == {
        "owned",
        "wishlist",
        "pre_order",
        "lent_out",
        "borrowed",
        "gifted_away",
        "sold",
        "lost",
    }


def test_book_status_exactly_one_target_check_constraint():
    constraints = [
        c for c in BookStatus.__table__.constraints if isinstance(c, CheckConstraint)
    ]
    assert any(c.name == "ck_book_status_exactly_one_target" for c in constraints)


def test_book_status_user_id_status_composite_index():
    indexes = [i for i in BookStatus.__table__.indexes if isinstance(i, Index)]
    assert any(i.name == "ix_book_statuses_user_id_status" for i in indexes)
