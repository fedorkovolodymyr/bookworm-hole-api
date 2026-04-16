# app/repositories/user_repository.py
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

from app.models.books import Book


class BookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, book: Book) -> Book:
        self.session.add(book)
        await self.session.commit()
        await self.session.refresh(book)
        return book

    async def get_by_id(self, book_id: int) -> Book | None:
        stmt = select(Book).where(Book.id == book_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 10) -> Sequence[Book]:
        stmt = select(Book).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(self, book_id: int, book_data: dict) -> Book | None:
        book = await self.get_by_id(book_id)
        if not book:
            return None

        for key, value in book_data.items():
            setattr(book, key, value)

        await self.session.commit()
        await self.session.refresh(book)
        return book

    async def delete(self, user_id: int) -> bool:
        user = await self.get_by_id(user_id)
        if not user:
            return False

        await self.session.delete(user)
        await self.session.commit()
        return True
