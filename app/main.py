from fastapi import FastAPI

from app.core.lifespan import lifespan
from app.routers.health import health_router

app = FastAPI(lifespan=lifespan)

app.include_router(health_router)
