from sqlalchemy import inspect

from app.models.contribution import Contribution, ContributionKind, ContributionStatus


def test_contribution_table_columns():
    columns = inspect(Contribution).columns
    expected = {
        "id",
        "user_id",
        "kind",
        "target_id",
        "payload",
        "status",
        "reviewer_id",
        "review_notes",
        "decided_at",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(columns.keys())
    assert columns["target_id"].nullable
    assert columns["reviewer_id"].nullable
    assert columns["review_notes"].nullable
    assert columns["decided_at"].nullable
    assert not columns["user_id"].nullable
    assert not columns["kind"].nullable
    assert not columns["payload"].nullable
    assert not columns["status"].nullable


def test_contribution_target_id_has_no_foreign_key():
    columns = inspect(Contribution).columns
    assert not columns["target_id"].foreign_keys


def test_contribution_kind_values():
    assert {kind.value for kind in ContributionKind} == {
        "new_book",
        "new_release",
        "new_contributor",
        "edit_book",
        "edit_release",
        "edit_contributor",
    }


def test_contribution_status_values():
    assert {status.value for status in ContributionStatus} == {
        "draft",
        "submitted",
        "under_review",
        "approved",
        "rejected",
        "merged",
    }


def test_contribution_status_defaults_to_draft():
    contribution = Contribution(
        user_id="00000000-0000-0000-0000-000000000001",
        kind=ContributionKind.new_book,
        payload={"schema_version": 1, "title": "New Book"},
    )
    assert contribution.status == ContributionStatus.draft
