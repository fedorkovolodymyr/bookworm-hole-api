from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.backup_record_repository import BackupRecordRepository


async def _make_user(db_session: AsyncSession, username: str) -> User:
    user = User(
        email=f"{username}@example.com", username=username, display_name=username
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestCreate:
    async def test_creates_record(self, db_session: AsyncSession):
        user = await _make_user(db_session, "owner")
        repository = BackupRecordRepository(db_session)

        record = await repository.create(
            user.id, "drive-file-id", "homelibrary-backup-1.json"
        )

        assert record.id is not None
        assert record.user_id == user.id
        assert record.drive_file_id == "drive-file-id"
        assert record.filename == "homelibrary-backup-1.json"
        assert record.created_at is not None


class TestGetAllForUser:
    async def test_returns_empty_for_user_with_no_backups(
        self, db_session: AsyncSession
    ):
        user = await _make_user(db_session, "owner")
        repository = BackupRecordRepository(db_session)

        items, total = await repository.get_all_for_user(user.id)

        assert items == []
        assert total == 0

    async def test_returns_newest_first(self, db_session: AsyncSession):
        user = await _make_user(db_session, "owner")
        repository = BackupRecordRepository(db_session)
        first = await repository.create(user.id, "file-1", "homelibrary-backup-1.json")
        second = await repository.create(user.id, "file-2", "homelibrary-backup-2.json")

        items, total = await repository.get_all_for_user(user.id)

        assert total == 2
        assert [item.id for item in items] == [second.id, first.id]

    async def test_paginates(self, db_session: AsyncSession):
        user = await _make_user(db_session, "owner")
        repository = BackupRecordRepository(db_session)
        for i in range(3):
            await repository.create(
                user.id, f"file-{i}", f"homelibrary-backup-{i}.json"
            )

        items, total = await repository.get_all_for_user(user.id, skip=1, limit=1)

        assert total == 3
        assert len(items) == 1

    async def test_scopes_to_user(self, db_session: AsyncSession):
        owner = await _make_user(db_session, "owner")
        other = await _make_user(db_session, "other")
        repository = BackupRecordRepository(db_session)
        await repository.create(owner.id, "file-1", "homelibrary-backup-1.json")
        await repository.create(other.id, "file-2", "homelibrary-backup-2.json")

        items, total = await repository.get_all_for_user(other.id)

        assert total == 1
        assert items[0].user_id == other.id
