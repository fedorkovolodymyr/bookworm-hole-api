from scripts.seed_data import DEV_BOOKS, DEV_CONTRIBUTORS, DEV_USERS


def test_dev_contributors_have_required_fields():
    for row in DEV_CONTRIBUTORS:
        assert row["full_name"]
        assert row["sort_name"]
        assert row["slug"]


def test_dev_books_have_required_fields():
    for row in DEV_BOOKS:
        assert row["title"]
        assert row["description"]


def test_dev_users_have_required_fields():
    for row in DEV_USERS:
        assert row["email"]
        assert row["username"]
        assert row["display_name"]
        assert row["password"]
