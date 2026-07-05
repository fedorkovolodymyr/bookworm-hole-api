from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError, ErrorMessages, NotFoundError
from app.models.review import Review
from app.repositories.review_repository import ReviewRepository, ReviewSort
from app.schemas.common_schemas import Page
from app.schemas.review_schemas import CreateReviewSchema, UpdateReviewSchema


class ReviewService:
    def __init__(self, repository: ReviewRepository):
        self.repository = repository

    async def _get_visible(self, user_id: UUID, review_id: UUID) -> Review:
        review = await self.repository.get_by_id(review_id)
        if not review or (not review.is_public and review.user_id != user_id):
            raise NotFoundError(ErrorMessages.REVIEW_NOT_FOUND)
        return review

    async def _get_owned(self, user_id: UUID, review_id: UUID) -> Review:
        review = await self.repository.get_by_id(review_id)
        if not review or review.user_id != user_id:
            raise NotFoundError(ErrorMessages.REVIEW_NOT_FOUND)
        return review

    async def create_review(self, user_id: UUID, data: CreateReviewSchema) -> Review:
        existing = await self.repository.get_by_user_and_target(
            user_id, data.book_id, data.release_id
        )
        if existing:
            raise ConflictError(ErrorMessages.REVIEW_ALREADY_EXISTS)
        review = Review(user_id=user_id, **data.model_dump())
        try:
            return await self.repository.create(review)
        except IntegrityError as exc:
            raise ConflictError(ErrorMessages.REVIEW_ALREADY_EXISTS) from exc

    async def get_review(self, user_id: UUID, review_id: UUID) -> Review:
        return await self._get_visible(user_id, review_id)

    async def update_review(
        self, user_id: UUID, review_id: UUID, data: UpdateReviewSchema
    ) -> Review:
        await self._get_owned(user_id, review_id)
        review = await self.repository.update(review_id, data)
        if not review:
            raise NotFoundError(ErrorMessages.REVIEW_NOT_FOUND)
        return review

    async def delete_review(self, user_id: UUID, review_id: UUID) -> None:
        await self._get_owned(user_id, review_id)
        deleted = await self.repository.delete(review_id)
        if not deleted:
            raise NotFoundError(ErrorMessages.REVIEW_NOT_FOUND)

    async def list_for_book(
        self, book_id: UUID, sort: ReviewSort, skip: int = 0, limit: int = 10
    ) -> Page[Review]:
        items, total = await self.repository.get_for_book(book_id, sort, skip, limit)
        return Page(items=list(items), total=total, limit=limit, offset=skip)

    async def list_for_release(
        self, release_id: UUID, sort: ReviewSort, skip: int = 0, limit: int = 10
    ) -> Page[Review]:
        items, total = await self.repository.get_for_release(
            release_id, sort, skip, limit
        )
        return Page(items=list(items), total=total, limit=limit, offset=skip)

    async def list_public_for_user(
        self, user_id: UUID, sort: ReviewSort, skip: int = 0, limit: int = 10
    ) -> Page[Review]:
        items, total = await self.repository.get_public_for_user(
            user_id, sort, skip, limit
        )
        return Page(items=list(items), total=total, limit=limit, offset=skip)
