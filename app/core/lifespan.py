from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    yield
    logger.info("Shutting down application...")
