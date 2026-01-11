from app.models.books import Book
from app.services.base_service import BaseService


class BookService(BaseService):
    model = Book
