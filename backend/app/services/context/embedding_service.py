from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Protocol, Sequence

import httpx

from app.core.config import settings


class EmbeddingServiceError(RuntimeError):
    pass


class EmbeddingDimensionMismatch(EmbeddingServiceError):
    pass


class EmbeddingService(Protocol):
    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        ...

    async def embed_query(self, text: str) -> list[float]:
        ...


@dataclass(frozen=True)
class EmbeddingGatewayConfig:
    base_url: str
    endpoint: str
    model: str
    api_key: str = ""
    timeout_seconds: float = 8.0


class BgeM3HttpEmbeddingService:
    """HTTP gateway for BGE-M3 style embeddings."""

    def __init__(self, *, config: EmbeddingGatewayConfig, http_client: httpx.AsyncClient) -> None:
        self._config = config
        self._http_client = http_client

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {
            "model": self._config.model,
            "input": list(texts),
        }
        endpoint = f"{self._config.base_url.rstrip('/')}/{self._config.endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        try:
            resp = await self._http_client.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self._config.timeout_seconds,
            )
            resp.raise_for_status()
            raw = resp.text
        except httpx.HTTPStatusError as exc:
            details = (exc.response.text or "")[:180]
            raise EmbeddingServiceError(f"embedding_http_error:{exc.response.status_code}:{details}") from exc
        except httpx.RequestError as exc:
            raise EmbeddingServiceError(f"embedding_connection_error:{exc.__class__.__name__}") from exc
        except Exception as exc:
            raise EmbeddingServiceError(f"embedding_connection_error:{exc.__class__.__name__}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EmbeddingServiceError("embedding_invalid_json") from exc

        vectors = self._extract_vectors(parsed)
        if len(vectors) != len(texts):
            raise EmbeddingServiceError("embedding_shape_mismatch")
        reported_dim = parsed.get("dim")
        if reported_dim is not None and int(reported_dim) != settings.embeddings_dim:
            raise EmbeddingDimensionMismatch(
                f"embedding_dim_mismatch:expected={settings.embeddings_dim}:reported={reported_dim}"
            )
        for vector in vectors:
            if len(vector) != settings.embeddings_dim:
                raise EmbeddingDimensionMismatch(
                    f"embedding_vector_dim_mismatch:expected={settings.embeddings_dim}:actual={len(vector)}"
                )
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_texts([text])
        return vectors[0] if vectors else []

    def _extract_vectors(self, payload: dict) -> list[list[float]]:
        # OpenAI-like shape: {"data":[{"embedding":[...]}]}
        if isinstance(payload.get("data"), list):
            out: list[list[float]] = []
            for row in payload["data"]:
                if not isinstance(row, dict):
                    continue
                embedding = row.get("embedding")
                if isinstance(embedding, list):
                    out.append([float(value) for value in embedding])
            if out:
                return out

        # Simple shape: {"embeddings":[[...] ...]}
        embeddings = payload.get("embeddings")
        if isinstance(embeddings, list):
            out = []
            for row in embeddings:
                if isinstance(row, list):
                    out.append([float(value) for value in row])
            if out:
                return out
        raise EmbeddingServiceError("embedding_payload_missing_vectors")


class FakeEmbeddingService:
    """Deterministic local embeddings for tests/dev fallback."""

    def __init__(self, *, dim: int = 64) -> None:
        if dim <= 0:
            raise ValueError("dim must be > 0")
        self._dim = dim

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dim
        tokens = [tok for tok in text.lower().split() if tok]
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(self._dim):
                byte_value = digest[i % len(digest)]
                signed = (byte_value / 255.0) * 2.0 - 1.0
                vector[i] += signed

        norm = math.sqrt(sum(value * value for value in vector))
        if norm <= 1e-9:
            return vector
        return [value / norm for value in vector]


class FallbackEmbeddingService:
    """Primary embedding provider with deterministic local fallback."""

    def __init__(
        self,
        *,
        primary: EmbeddingService,
        fallback: EmbeddingService,
        use_fallback_on_error: bool,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._use_fallback_on_error = use_fallback_on_error
        self.last_provider: str = "primary"

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            vectors = await self._primary.embed_texts(texts)
            self.last_provider = "primary"
            return vectors
        except Exception:
            if not self._use_fallback_on_error:
                raise
            self.last_provider = "fallback"
            return await self._fallback.embed_texts(texts)

    async def embed_query(self, text: str) -> list[float]:
        try:
            vector = await self._primary.embed_query(text)
            self.last_provider = "primary"
            return vector
        except Exception:
            if not self._use_fallback_on_error:
                raise
            self.last_provider = "fallback"
            return await self._fallback.embed_query(text)
