from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from app.api.v1.endpoints.health import assert_startup_embedding_dim_contract
from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await assert_startup_embedding_dim_contract()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(v1_router)
app.include_router(api_router)
