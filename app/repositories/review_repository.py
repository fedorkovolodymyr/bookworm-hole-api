from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement
from sqlmodel import col, select

from app.models.catalog import Release
from app.models.review import Review
from app.schemas.review_schemas import UpdateReviewSchema

ReviewSort = Literal["created_at", "rating"]

SORTABLE_FIELDS = {"created_at": Review.created_at, "rating": Review.rating}


class ReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, review: Review) -> Review:
        self.session.add(review)
        await self.session.commit()
        await self.session.refresh(review)
        return review

    async def get_by_id(self, review_id: UUID) -> Review | None:
        return await self.session.get(Review, review_id, populate_existing=True)

    async def get_by_user_and_target(
        self, user_id: UUID, book_id: UUID | None, release_id: UUID | None
    ) -> Review | None:
        query = select(Review).where(col(Review.user_id) == user_id)
        query = (
            query.where(col(Review.book_id) == book_id)
            if book_id is not None
            else query.where(col(Review.release_id) == release_id)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def update(self, review_id: UUID, data: UpdateReviewSchema) -> Review | None:
        review = await self.session.get(Review, review_id)
        if not review:
            return None
        review.sqlmodel_update(data.model_dump(exclude_unset=True))
        self.session.add(review)
        await self.session.commit()
        await self.session.refresh(review)
        return review

    async def delete(self, review_id: UUID) -> bool:
        review = await self.session.get(Review, review_id)
        if not review:
            return False
        await self.session.delete(review)
        await self.session.commit()
        return True

    async def get_for_book(
        self, book_id: UUID, sort: ReviewSort, skip: int = 0, limit: int = 10
    ) -> tuple[Sequence[Review], int]:
        count_query = select(func.count()).select_from(
            select(Review.id)
            .where(col(Review.book_id) == book_id, col(Review.is_public).is_(True))
            .subquery()
        )
        total = (await self.session.execute(count_query)).scalar_one()
        query = (
            select(Review)
            .where(col(Review.book_id) == book_id, col(Review.is_public).is_(True))
            .order_by(col(SORTABLE_FIELDS[sort]).desc())
        )
        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def get_for_release(
        self, release_id: UUID, sort: ReviewSort, skip: int = 0, limit: int = 10
    ) -> tuple[Sequence[Review], int]:
        count_query = select(func.count()).select_from(
            select(Review.id)
            .where(
                col(Review.release_id) == release_id, col(Review.is_public).is_(True)
            )
            .subquery()
        )
        total = (await self.session.execute(count_query)).scalar_one()
        query = (
            select(Review)
            .where(
                col(Review.release_id) == release_id, col(Review.is_public).is_(True)
            )
            .order_by(col(SORTABLE_FIELDS[sort]).desc())
        )
        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def get_public_for_user(
        self, user_id: UUID, sort: ReviewSort, skip: int = 0, limit: int = 10
    ) -> tuple[Sequence[Review], int]:
        count_query = select(func.count()).select_from(
            select(Review.id)
            .where(col(Review.user_id) == user_id, col(Review.is_public).is_(True))
            .subquery()
        )
        total = (await self.session.execute(count_query)).scalar_one()
        query = (
            select(Review)
            .where(col(Review.user_id) == user_id, col(Review.is_public).is_(True))
            .order_by(col(SORTABLE_FIELDS[sort]).desc())
        )
        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def get_rating_aggregate_for_book(
        self, book_id: UUID
    ) -> tuple[float | None, int]:
        release_ids_query = select(Release.id).where(col(Release.book_id) == book_id)
        release_ids_result = await self.session.execute(release_ids_query)
        release_ids: list[UUID] = [row[0] for row in release_ids_result.all()]

        target_conditions: list[ColumnElement[bool]] = [col(Review.book_id) == book_id]
        if release_ids:
            target_conditions.append(col(Review.release_id).in_(release_ids))

        query = select(func.avg(Review.rating), func.count(col(Review.id))).where(
            and_(col(Review.is_public).is_(True), or_(*target_conditions))
        )
        result = await self.session.execute(query)
        row = result.first()
        avg_rating: float | None = float(row[0]) if row and row[0] is not None else None
        count: int = row[1] if row else 0
        return avg_rating, count or 0

    async def get_rating_aggregate_for_release(
        self, release_id: UUID
    ) -> tuple[float | None, int]:
        query = select(func.avg(Review.rating), func.count(col(Review.id))).where(
            and_(col(Review.release_id) == release_id, col(Review.is_public).is_(True))
        )
        result = await self.session.execute(query)
        row = result.first()
        avg_rating: float | None = float(row[0]) if row and row[0] is not None else None
        count: int = row[1] if row else 0
        return avg_rating, count or 0

    async def get_all_for_user(self, user_id: UUID) -> Sequence[Review]:
        query = select(Review).where(col(Review.user_id) == user_id)
        result = await self.session.execute(query)
        return result.scalars().all()
