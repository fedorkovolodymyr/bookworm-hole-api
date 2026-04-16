from ast import stmt
from turtle import up
from typing import Sequence

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.books import Book
from app.repositories.boock_repository import BookRepository
from app.schemas.book_schemas import CreateBookSchema, UpdateBookSchema


class BookService:
    model = Book

    def __init__(self, repository: BookRepository):
        self.repository = repository

    async def create_book(self, new_book: CreateBookSchema) -> Book:
        book = Book(**new_book.model_dump())
        return await self.repository.create(book)

    async def retrieve_book_by_id(self, book_id: int) -> Book | None:
        return await self.repository.get_by_id(book_id)

    async def retrieve_all_books(self, skip: int = 0, limit: int = 10) -> Sequence[Book]:
        return await self.repository.get_all(skip, limit)

    # async def update_user(self, user_id: int, **kwargs) -> User | None:
    #     # Бізнес логіка: невалідні поля
    #     invalid_fields = {"id", "created_at"}
    #     for field in invalid_fields:
    #         kwargs.pop(field, None)

    #     return await self.repository.update(user_id, kwargs)

    # async def delete_user(self, user_id: int) -> bool:
    #     return await self.repository.delete(user_id)

    #### old code ####

    # async def get_all(self, session: AsyncSession) -> list[Book]:
    #     stmt = select(self.model)
    #     result = await session.execute(stmt)
    #     return list(result.scalars().all())

    # async def get_by_id(self, book_id: int, session: AsyncSession) -> Book | None:
    #     stmt = select(self.model).where(self.model.id == book_id)
    #     result = await session.execute(stmt)
    #     return result.scalar_one_or_none()

    # async def create(self, new_book: CreateBookSchema, session: AsyncSession) -> Book:
    #     stmt = insert(self.model).values(**new_book.model_dump()).returning(self.model)
    #     result = await session.execute(stmt)
    #     await session.commit()
    #     return result.scalar_one()

    # async def update(
    #     self, book_id: int, updated_data: UpdateBookSchema, session: AsyncSession
    # ) -> Book:
    #     stmt = (
    #         update(self.model)
    #         .where(self.model.id == book_id)
    #         .values(**updated_data.model_dump(exclude_unset=True))
    #         .returning(self.model)
    #     )
    #     result = await session.execute(stmt)
    #     await session.commit()
    #     return result.scalar_one()
