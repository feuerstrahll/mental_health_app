from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.context.memory_index_service import (
    MemoryChunk,
    MemoryChunkStore,
    MemoryEmbeddingStore,
    RetrievedMemory,
    StoredMemoryEmbedding,
)


def _vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(f"{float(v):.8f}" for v in values) + "]"


class PostgresMemoryChunkStore(MemoryChunkStore):
    def __init__(self, *, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def upsert_chunks(self, chunks: Sequence[MemoryChunk]) -> None:
        if not chunks:
            return
        query = text(
            """
            INSERT INTO memory_chunks (
                id,
                user_id,
                source_type,
                source_id,
                text,
                content_hash,
                importance_score,
                expires_at,
                created_at,
                metadata_jsonb,
                is_current_turn,
                request_id
            )
            VALUES (
                :id,
                :user_id,
                :source_type,
                :source_id,
                :text,
                :content_hash,
                :importance_score,
                :expires_at,
                :created_at,
                CAST(:metadata_jsonb AS jsonb),
                :is_current_turn,
                :request_id
            )
            ON CONFLICT (user_id, source_type, source_id, content_hash)
            DO UPDATE SET
                text = EXCLUDED.text,
                metadata_jsonb = EXCLUDED.metadata_jsonb,
                is_current_turn = EXCLUDED.is_current_turn,
                request_id = EXCLUDED.request_id
            """
        )
        async with self._session_maker() as session:
            for chunk in chunks:
                await session.execute(
                    query,
                    {
                        "id": chunk.id,
                        "user_id": chunk.user_id,
                        "source_type": chunk.source_type,
                        "source_id": chunk.source_id,
                        "text": chunk.text,
                        "content_hash": chunk.content_hash,
                        "importance_score": None,
                        "expires_at": None,
                        "created_at": datetime.utcnow(),
                        "metadata_jsonb": json.dumps(dict(chunk.metadata or {}), ensure_ascii=False),
                        "is_current_turn": bool(chunk.is_current_turn),
                        "request_id": chunk.request_id,
                    },
                )
            await session.commit()


class PostgresMemoryEmbeddingStore(MemoryEmbeddingStore):
    def __init__(self, *, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def get_hash_by_chunk_ids(
        self,
        *,
        user_id: str,
        chunk_ids: Sequence[str],
        model: str,
        dim: int,
    ) -> dict[str, str]:
        if not chunk_ids:
            return {}
        query = (
            text(
                """
                SELECT memory_chunk_id, content_hash
                FROM user_memory_embeddings
                WHERE user_id = :user_id
                  AND model = :model
                  AND dim = :dim
                  AND memory_chunk_id IN :chunk_ids
                """
            )
            .bindparams(bindparam("chunk_ids", expanding=True))
        )
        async with self._session_maker() as session:
            rows = (await session.execute(query, {"user_id": user_id, "model": model, "dim": dim, "chunk_ids": list(chunk_ids)})).mappings()
            return {str(row["memory_chunk_id"]): str(row["content_hash"]) for row in rows}

    async def upsert_records(self, records: Sequence[StoredMemoryEmbedding]) -> None:
        if not records:
            return
        query = text(
            """
            INSERT INTO user_memory_embeddings (
                id,
                user_id,
                memory_chunk_id,
                source_type,
                date,
                text,
                model,
                dim,
                embedding,
                content_hash,
                created_at,
                metadata_jsonb
            )
            VALUES (
                :id,
                :user_id,
                :memory_chunk_id,
                :source_type,
                :date,
                :text,
                :model,
                :dim,
                CAST(:embedding AS vector),
                :content_hash,
                :created_at,
                CAST(:metadata_jsonb AS jsonb)
            )
            ON CONFLICT (memory_chunk_id, model, dim)
            DO UPDATE SET
                user_id = EXCLUDED.user_id,
                embedding = EXCLUDED.embedding,
                content_hash = EXCLUDED.content_hash,
                created_at = EXCLUDED.created_at,
                metadata_jsonb = EXCLUDED.metadata_jsonb
            """
        )
        async with self._session_maker() as session:
            for record in records:
                await session.execute(
                    query,
                    {
                        "id": record.id,
                        "user_id": record.user_id,
                        "memory_chunk_id": record.memory_chunk_id,
                        "source_type": record.source_type,
                        "date": record.date,
                        "text": record.text,
                        "model": record.model,
                        "dim": record.dim,
                        "embedding": _vector_literal(record.embedding),
                        "content_hash": record.content_hash,
                        "created_at": record.created_at,
                        "metadata_jsonb": json.dumps(dict(record.metadata or {}), ensure_ascii=False),
                    },
                )
            await session.commit()

    async def search(
        self,
        *,
        user_id: str,
        query_embedding: Sequence[float],
        top_k: int,
        days_back: int,
        model: str,
        dim: int,
        include_current_turn: bool = False,
        exclude_source_ids: Sequence[str] | None = None,
    ) -> list[RetrievedMemory]:
        if top_k <= 0:
            return []
        excluded_ids = [str(value) for value in (exclude_source_ids or []) if str(value).strip()]
        exclude_enabled = bool(excluded_ids)
        query = text(
            """
            SELECT
                e.memory_chunk_id,
                e.source_type,
                m.source_id,
                e.text,
                m.metadata_jsonb,
                e.date,
                (1 - (e.embedding <=> CAST(:query_embedding AS vector))) AS score
            FROM user_memory_embeddings e
            INNER JOIN memory_chunks m ON m.id = e.memory_chunk_id
            WHERE e.user_id = :user_id
              AND e.model = :model
              AND e.dim = :dim
              AND m.user_id = :user_id
              AND CAST(e.date AS date) >= CURRENT_DATE - CAST(:days_back AS integer)
              AND (m.expires_at IS NULL OR m.expires_at > NOW())
              AND (:include_current_turn OR m.is_current_turn = FALSE)
              AND (NOT :exclude_enabled OR m.source_id NOT IN :exclude_source_ids)
            ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
            """
        ).bindparams(bindparam("exclude_source_ids", expanding=True))
        async with self._session_maker() as session:
            rows = (
                await session.execute(
                    query,
                    {
                        "user_id": user_id,
                        "model": model,
                        "dim": dim,
                        "query_embedding": _vector_literal(query_embedding),
                        "days_back": max(days_back, 1),
                        "include_current_turn": bool(include_current_turn),
                        "exclude_enabled": exclude_enabled,
                        "exclude_source_ids": excluded_ids if excluded_ids else [""],
                        "top_k": top_k,
                    },
                )
            ).mappings()
            out: list[RetrievedMemory] = []
            for row in rows:
                out.append(
                    RetrievedMemory(
                        memory_chunk_id=str(row["memory_chunk_id"]),
                        source_type=str(row["source_type"]),
                        source_id=str(row["source_id"]),
                        date=str(row["date"]),
                        text=str(row["text"]),
                        metadata=dict(row.get("metadata_jsonb") or {}),
                        score=float(row["score"] or 0.0),
                    )
                )
            return out
