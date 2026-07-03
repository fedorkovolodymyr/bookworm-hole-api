from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException

from app.models.book_status import BookStatus, BookStatusKind
from app.repositories.book_status_repository import BookStatusRepository
from app.schemas.book_status_schemas import (
    CreateBookStatusSchema,
    LendBookStatusSchema,
    UpdateBookStatusSchema,
)


class BookStatusService:
    def __init__(self, repository: BookStatusRepository):
        self.repository = repository

    async def create_status(
        self, user_id: UUID, new_status: CreateBookStatusSchema
    ) -> BookStatus:
        book_status = BookStatus(
            user_id=user_id,
            acquired_at=datetime.now(UTC),
            **new_status.model_dump(),
        )
        return await self.repository.create(book_status)

    async def list_statuses(
        self, user_id: UUID, status: BookStatusKind | None = None
    ) -> list[BookStatus]:
        return list(await self.repository.get_all_for_user(user_id, status))

    async def _retrieve_owned(self, user_id: UUID, book_status_id: UUID) -> BookStatus:
        book_status = await self.repository.get_by_id(book_status_id)
        if not book_status or book_status.user_id != user_id:
            raise HTTPException(status_code=404, detail="Status not found")
        return book_status

    async def modify_status(
        self,
        user_id: UUID,
        book_status_id: UUID,
        updated_status: UpdateBookStatusSchema,
    ) -> BookStatus:
        await self._retrieve_owned(user_id, book_status_id)
        book_status = await self.repository.update(book_status_id, updated_status)
        if not book_status:
            raise HTTPException(status_code=404, detail="Status not found")
        return book_status

    async def delete_status(self, user_id: UUID, book_status_id: UUID) -> None:
        await self._retrieve_owned(user_id, book_status_id)
        deleted = await self.repository.delete(book_status_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Status not found")

    async def lend_status(
        self, user_id: UUID, book_status_id: UUID, lend: LendBookStatusSchema
    ) -> BookStatus:
        book_status = await self._retrieve_owned(user_id, book_status_id)
        if book_status.status != BookStatusKind.owned:
            raise HTTPException(
                status_code=409, detail="Only an owned status can be lent out"
            )
        book_status.status = BookStatusKind.lent_out
        book_status.lent_to_user_id = lend.lent_to_user_id
        book_status.lent_to_name = lend.lent_to_name
        book_status.lent_at = datetime.now(UTC)
        book_status.returned_at = None
        return await self.repository.save(book_status)

    async def return_status(self, user_id: UUID, book_status_id: UUID) -> BookStatus:
        book_status = await self._retrieve_owned(user_id, book_status_id)
        if book_status.status != BookStatusKind.lent_out:
            raise HTTPException(
                status_code=409, detail="Only a lent-out status can be returned"
            )
        book_status.status = BookStatusKind.owned
        book_status.returned_at = datetime.now(UTC)
        book_status.lent_to_user_id = None
        book_status.lent_to_name = None
        return await self.repository.save(book_status)
