from fastapi import APIRouter

from app.routers.auth import auth_router
from app.routers.books import books_router
from app.routers.collections import collections_router
from app.routers.contributors import contributors_router
from app.routers.external import external_router
from app.routers.friends import friends_router
from app.routers.health import health_router
from app.routers.releases import releases_router
from app.routers.reviews import reviews_router
from app.routers.status_views import status_views_router
from app.routers.statuses import statuses_router
from app.routers.users import users_router

api_v1 = APIRouter(prefix="/api/v1")

api_v1.include_router(health_router)
api_v1.include_router(books_router)
api_v1.include_router(releases_router)
api_v1.include_router(contributors_router)
api_v1.include_router(auth_router)
api_v1.include_router(statuses_router)
api_v1.include_router(status_views_router)
api_v1.include_router(collections_router)
api_v1.include_router(external_router)
api_v1.include_router(friends_router)
api_v1.include_router(reviews_router)
api_v1.include_router(users_router)
