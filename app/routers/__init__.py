from fastapi import APIRouter

from app.routers.auth import auth_router
from app.routers.books import books_router
from app.routers.collections import collections_router
from app.routers.external import external_router
from app.routers.health import health_router
from app.routers.releases import releases_router
from app.routers.statuses import statuses_router

api_v1 = APIRouter(prefix="/api/v1")

api_v1.include_router(health_router)
api_v1.include_router(books_router)
api_v1.include_router(releases_router)
api_v1.include_router(auth_router)
api_v1.include_router(statuses_router)
api_v1.include_router(collections_router)
api_v1.include_router(external_router)
