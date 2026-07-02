from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.core.lifespan import lifespan
from app.routers import api_v1

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().app_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1)


@app.get("/health", include_in_schema=False)
async def health(settings: Settings = Depends(get_settings)) -> JSONResponse:
    return JSONResponse({"status": "ok", "app_env": settings.app_settings.app_env})
