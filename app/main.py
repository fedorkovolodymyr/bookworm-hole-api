from fastapi import FastAPI

from app.core.lifespan import lifespan
from app.routers import api_v1

app = FastAPI(lifespan=lifespan)

app.include_router(api_v1)
