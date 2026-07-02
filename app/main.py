from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.lifespan import lifespan
from app.routers import api_v1

app = FastAPI(lifespan=lifespan)

app.include_router(api_v1)


@app.get("/health", include_in_schema=False)
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
