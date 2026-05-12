from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from FlagEmbedding import BGEM3FlagModel
except ImportError:  # pragma: no cover - startup dependency guard
    BGEM3FlagModel = None  # type: ignore[assignment]


MODEL_NAME = os.getenv("BGE_MODEL_NAME", "BAAI/bge-m3")
BATCH_SIZE = int(os.getenv("BGE_BATCH_SIZE", "1"))
MAX_LENGTH = int(os.getenv("BGE_MAX_LENGTH", "512"))


class EmbedRequest(BaseModel):
    text: str | None = None
    texts: list[str] | None = None
    input: str | list[str] | None = Field(default=None)
    model: str | None = None


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    model: str
    dim: int


class AppState:
    model: Any | None = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if BGEM3FlagModel is None:
        raise RuntimeError("FlagEmbedding is not installed")
    state.model = BGEM3FlagModel(MODEL_NAME, use_fp16=False)
    yield


app = FastAPI(title="BGE Embedding Service", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/embed", response_model=EmbedResponse)
def embed(request: EmbedRequest) -> EmbedResponse:
    texts = _extract_texts(request)
    if not texts:
        raise HTTPException(status_code=400, detail="No text provided")
    if state.model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")

    result = state.model.encode(
        texts,
        batch_size=BATCH_SIZE,
        max_length=MAX_LENGTH,
    )
    vectors = result.get("dense_vecs")
    if vectors is None:
        raise HTTPException(status_code=500, detail="Dense embeddings missing")

    embeddings = [[float(value) for value in vector] for vector in vectors]
    dim = len(embeddings[0]) if embeddings else 0
    return EmbedResponse(embeddings=embeddings, model=MODEL_NAME, dim=dim)


def _extract_texts(request: EmbedRequest) -> list[str]:
    if request.text is not None:
        return [request.text]
    if request.texts is not None:
        return request.texts
    if isinstance(request.input, str):
        return [request.input]
    if isinstance(request.input, list):
        return request.input
    return []
