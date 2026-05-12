from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.context.embedding_service import BgeM3HttpEmbeddingService, EmbeddingGatewayConfig
from app.services.context.memory_index_service import MemoryIndexService
from app.services.context.user_memory_chunk_service import UserMemoryChunk
from app.repositories.postgres.memory_store import PostgresMemoryChunkStore, PostgresMemoryEmbeddingStore


class _FakeBgeResponse:
    status_code = 200

    def __init__(self, count: int, dim: int) -> None:
        vector = [0.0] * dim
        vector[0] = 1.0
        self._payload = {
            "embeddings": [list(vector) for _ in range(count)],
            "model": "fake-bge-m3",
            "dim": dim,
        }
        import json

        self.text = json.dumps(self._payload)

    def raise_for_status(self) -> None:
        return None


class _FakeBgeHttpClient:
    def __init__(self, *, dim: int) -> None:
        self.dim = dim
        self.calls: list[dict[str, Any]] = []

    async def post(self, *args: Any, **kwargs: Any) -> _FakeBgeResponse:
        payload = dict(kwargs.get("json") or {})
        values = payload.get("input") or []
        if isinstance(values, str):
            count = 1
        else:
            count = len(values)
        self.calls.append(payload)
        return _FakeBgeResponse(count=count, dim=self.dim)


def test_live_postgres_bge_embedding_insert_and_retrieval() -> None:
    dsn = os.getenv("LIVE_POSTGRES_DSN")
    if not dsn:
        pytest.skip("Set LIVE_POSTGRES_DSN to run live Postgres + BGE memory integration test")

    import asyncio

    async_dsn = _async_postgres_dsn(dsn)
    _apply_memory_migrations(async_dsn)
    asyncio.run(_run_live_postgres_bge_case(async_dsn))


def _apply_memory_migrations(dsn: str) -> None:
    backend_dir = Path(__file__).resolve().parents[3]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", dsn)
    command.upgrade(alembic_cfg, "20260501_0003")


async def _run_live_postgres_bge_case(dsn: str) -> None:
    engine = create_async_engine(dsn)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    user_id = "it_user_bge_pg_contract"
    chunk = UserMemoryChunk(
        id="it_chunk_bge_pg_contract",
        user_id=user_id,
        date="2026-05-01",
        source_type="chat_message",
        source_id="it_source_bge_pg_contract",
        text="Date: 2026-05-01. Integration memory text.",
        metadata={"test_case": "bge_postgres_memory_e2e"},
        content_hash="it_hash_bge_pg_contract",
        is_current_turn=False,
        request_id="it_req_bge_pg_contract",
    )

    try:
        await _cleanup_test_rows(session_maker, user_id=user_id)
        fake_bge = _FakeBgeHttpClient(dim=1024)
        embedding_service = BgeM3HttpEmbeddingService(
            config=EmbeddingGatewayConfig(
                base_url="http://fake-bge",
                endpoint="/embed",
                model="BAAI/bge-m3",
            ),
            http_client=fake_bge,
        )
        memory_index = MemoryIndexService(
            embedding_service=embedding_service,
            chunk_store=PostgresMemoryChunkStore(session_maker=session_maker),
            embedding_store=PostgresMemoryEmbeddingStore(session_maker=session_maker),
            model="BAAI/bge-m3",
            dim=1024,
            batch_size=8,
        )

        upsert = await memory_index.upsert_chunks(user_id=user_id, chunks=[chunk])
        assert upsert.indexed_count == 1
        assert upsert.reembedded_count == 1
        assert fake_bge.calls[0]["input"] == [chunk.text]

        async with session_maker() as session:
            row = (
                await session.execute(
                    text(
                        """
                        SELECT user_id, memory_chunk_id, source_type, date, text, dim, embedding::text AS embedding_text
                        FROM user_memory_embeddings
                        WHERE user_id = :user_id AND memory_chunk_id = :chunk_id
                        """
                    ),
                    {"user_id": user_id, "chunk_id": chunk.id},
                )
            ).mappings().one()
        assert row["user_id"] == user_id
        assert row["memory_chunk_id"] == chunk.id
        assert row["source_type"] == chunk.source_type
        assert row["date"] == chunk.date
        assert row["text"] == chunk.text
        assert row["dim"] == 1024
        assert row["embedding_text"]

        retrieved = await memory_index.retrieve_relevant(
            user_id=user_id,
            query_text="integration memory",
            days_back=30,
            top_k=3,
        )
        assert len(retrieved) >= 1
        first = retrieved[0]
        assert first.memory_chunk_id == chunk.id
        assert first.source_type == chunk.source_type
        assert first.source_id == chunk.source_id
        assert first.text == chunk.text
        assert first.date == chunk.date
    finally:
        await _cleanup_test_rows(session_maker, user_id=user_id)
        await engine.dispose()


def _async_postgres_dsn(dsn: str) -> str:
    if dsn.startswith("postgresql+asyncpg://"):
        return dsn
    if dsn.startswith("postgresql://"):
        return "postgresql+asyncpg://" + dsn.removeprefix("postgresql://")
    if dsn.startswith("postgres://"):
        return "postgresql+asyncpg://" + dsn.removeprefix("postgres://")
    return dsn


async def _cleanup_test_rows(session_maker: async_sessionmaker, *, user_id: str) -> None:
    async with session_maker() as session:
        await session.execute(text("DELETE FROM user_memory_embeddings WHERE user_id = :user_id"), {"user_id": user_id})
        await session.execute(text("DELETE FROM memory_chunks WHERE user_id = :user_id"), {"user_id": user_id})
        await session.commit()
