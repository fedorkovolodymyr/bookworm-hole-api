from sqlalchemy import CheckConstraint, inspect

from app.models.collection import Collection, CollectionItem


def test_collection_table_columns():
    columns = inspect(Collection).columns
    expected = {
        "id",
        "user_id",
        "name",
        "description",
        "is_public",
        "cover_image_url",
        "sort_order",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(columns.keys())
    assert columns["description"].nullable
    assert columns["cover_image_url"].nullable


def test_collection_defaults():
    collection = Collection(
        user_id="00000000-0000-0000-0000-000000000000", name="Favourites"
    )
    assert collection.is_public is False
    assert collection.sort_order == 0
    assert collection.description is None


def test_collection_items_relationship():
    relationship = inspect(Collection).relationships["items"]
    assert relationship.mapper.class_ is CollectionItem
    assert relationship.back_populates == "collection"


def test_collection_item_table_columns():
    columns = inspect(CollectionItem).columns
    expected = {
        "id",
        "collection_id",
        "book_id",
        "release_id",
        "position",
        "added_at",
        "note",
    }
    assert expected.issubset(columns.keys())
    assert columns["book_id"].nullable
    assert columns["release_id"].nullable


def test_collection_item_collection_relationship():
    relationship = inspect(CollectionItem).relationships["collection"]
    assert relationship.mapper.class_ is Collection
    assert relationship.back_populates == "items"


def test_collection_item_exactly_one_target_check_constraint():
    constraints = [
        c
        for c in CollectionItem.__table__.constraints
        if isinstance(c, CheckConstraint)
    ]
    assert any(c.name == "ck_collection_item_exactly_one_target" for c in constraints)
