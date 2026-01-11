from fastapi import APIRouter

from app.routers.books import books_router
from app.routers.health import health_router

api_v1 = APIRouter(prefix="/api/v1")

api_v1.include_router(health_router)
api_v1.include_router(books_router)
