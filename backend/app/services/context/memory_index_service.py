from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from math import sqrt
from typing import Any, Protocol, Sequence

from app.services.context.embedding_service import EmbeddingService
from app.services.context.user_memory_chunk_service import UserMemoryChunk


@dataclass(frozen=True)
class MemoryChunk:
    id: str
    user_id: str
    date: str
    source_type: str
    source_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    is_current_turn: bool = False
    request_id: str | None = None


@dataclass(frozen=True)
class RetrievedMemory:
    memory_chunk_id: str
    source_type: str
    source_id: str
    date: str
    text: str
    metadata: dict[str, Any]
    score: float


@dataclass(frozen=True)
class StoredMemoryEmbedding:
    id: str
    user_id: str
    memory_chunk_id: str
    source_type: str
    source_id: str
    date: str
    text: str
    model: str
    dim: int
    embedding: list[float]
    content_hash: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryChunkStore(Protocol):
    async def upsert_chunks(self, chunks: Sequence[MemoryChunk]) -> None:
        ...


class MemoryEmbeddingStore(Protocol):
    async def get_hash_by_chunk_ids(
        self,
        *,
        user_id: str,
        chunk_ids: Sequence[str],
        model: str,
        dim: int,
    ) -> dict[str, str]:
        ...

    async def upsert_records(self, records: Sequence[StoredMemoryEmbedding]) -> None:
        ...

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
        ...


class InMemoryChunkStore(MemoryChunkStore):
    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str, str], MemoryChunk] = {}

    async def upsert_chunks(self, chunks: Sequence[MemoryChunk]) -> None:
        for chunk in chunks:
            key = (chunk.user_id, chunk.source_type, chunk.source_id, chunk.content_hash)
            self._records[key] = chunk


class InMemoryEmbeddingStore(MemoryEmbeddingStore):
    """Simple deterministic store for local/dev/tests."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, int], StoredMemoryEmbedding] = {}
        self._chunk_map: dict[str, MemoryChunk] = {}

    async def set_chunk_records(self, chunks: Sequence[MemoryChunk]) -> None:
        for chunk in chunks:
            self._chunk_map[chunk.id] = chunk

    async def get_hash_by_chunk_ids(
        self,
        *,
        user_id: str,
        chunk_ids: Sequence[str],
        model: str,
        dim: int,
    ) -> dict[str, str]:
        out: dict[str, str] = {}
        for chunk_id in chunk_ids:
            record = self._records.get((chunk_id, model, dim))
            if record is not None and record.user_id == user_id:
                out[chunk_id] = record.content_hash
        return out

    async def upsert_records(self, records: Sequence[StoredMemoryEmbedding]) -> None:
        for record in records:
            self._records[(record.memory_chunk_id, record.model, record.dim)] = record

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
        cutoff = date.today() - timedelta(days=max(days_back, 1))
        excluded_ids = {str(value) for value in (exclude_source_ids or []) if str(value).strip()}
        rows: list[RetrievedMemory] = []
        for (chunk_id, row_model, row_dim), record in self._records.items():
            if row_model != model or row_dim != dim or record.user_id != user_id:
                continue
            chunk = self._chunk_map.get(chunk_id)
            if chunk is None:
                continue
            if chunk.source_id in excluded_ids:
                continue
            if chunk.is_current_turn and not include_current_turn:
                continue
            parsed_date = _parse_iso_date(chunk.date)
            if parsed_date and parsed_date < cutoff:
                continue
            score = _cosine_similarity(query_embedding, record.embedding)
            rows.append(
                RetrievedMemory(
                    memory_chunk_id=record.memory_chunk_id,
                    source_type=chunk.source_type,
                    source_id=chunk.source_id,
                    date=chunk.date,
                    text=chunk.text,
                    metadata=dict(chunk.metadata),
                    score=score,
                )
            )
        rows.sort(key=lambda item: item.score, reverse=True)
        return rows[:top_k]


@dataclass(frozen=True)
class UpsertResult:
    indexed_count: int
    upserted_count: int
    reembedded_count: int
    skipped_count: int
    used_embedding_provider: str


@dataclass(frozen=True)
class IndexResult:
    retrieved_memories: list[RetrievedMemory]
    indexed_count: int
    reembedded_count: int
    skipped_count: int
    used_embedding_provider: str


class MemoryIndexService:
    def __init__(
        self,
        *,
        embedding_service: EmbeddingService,
        chunk_store: MemoryChunkStore,
        embedding_store: MemoryEmbeddingStore,
        model: str,
        dim: int,
        batch_size: int = 24,
    ) -> None:
        self._embedding_service = embedding_service
        self._chunk_store = chunk_store
        self._embedding_store = embedding_store
        self._model = model
        self._dim = dim
        self._batch_size = max(1, batch_size)

    async def upsert_chunks(
        self,
        *,
        user_id: str,
        chunks: Sequence[UserMemoryChunk] | Sequence[MemoryChunk],
    ) -> UpsertResult:
        normalized = [self._normalize_chunk(chunk) for chunk in chunks]
        if not normalized:
            return UpsertResult(
                indexed_count=0,
                upserted_count=0,
                reembedded_count=0,
                skipped_count=0,
                used_embedding_provider=self._provider_name(),
            )
        await self._chunk_store.upsert_chunks(normalized)
        if isinstance(self._embedding_store, InMemoryEmbeddingStore):
            await self._embedding_store.set_chunk_records(normalized)

        existing_hashes = await self._embedding_store.get_hash_by_chunk_ids(
            user_id=user_id,
            chunk_ids=[chunk.id for chunk in normalized],
            model=self._model,
            dim=self._dim,
        )
        to_reembed = [chunk for chunk in normalized if existing_hashes.get(chunk.id) != chunk.content_hash]
        skipped_count = len(normalized) - len(to_reembed)

        now = datetime.utcnow()
        upserts: list[StoredMemoryEmbedding] = []
        for batch in _batched(to_reembed, self._batch_size):
            texts = [chunk.text for chunk in batch]
            vectors = await self._embedding_service.embed_texts(texts)
            for chunk, vector in zip(batch, vectors, strict=True):
                upserts.append(
                    StoredMemoryEmbedding(
                        id=f"{chunk.id}:{self._model}:{self._dim}",
                        user_id=user_id,
                        memory_chunk_id=chunk.id,
                        source_type=chunk.source_type,
                        source_id=chunk.source_id,
                        date=chunk.date,
                        text=chunk.text,
                        model=self._model,
                        dim=self._dim,
                        embedding=list(vector),
                        content_hash=chunk.content_hash,
                        created_at=now,
                        metadata={
                            "source_type": chunk.source_type,
                            "source_id": chunk.source_id,
                            "request_id": chunk.request_id,
                            "is_current_turn": chunk.is_current_turn,
                        },
                    )
                )
        if upserts:
            await self._embedding_store.upsert_records(upserts)
        return UpsertResult(
            indexed_count=len(normalized),
            upserted_count=len(normalized),
            reembedded_count=len(upserts),
            skipped_count=skipped_count,
            used_embedding_provider=self._provider_name(),
        )

    async def retrieve_relevant(
        self,
        *,
        user_id: str,
        query_text: str,
        days_back: int = 14,
        top_k: int = 6,
        include_current_turn: bool = False,
        exclude_source_ids: Sequence[str] | None = None,
    ) -> list[RetrievedMemory]:
        query_embedding = await self._embedding_service.embed_query(query_text or "")
        return await self._embedding_store.search(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=top_k,
            days_back=days_back,
            model=self._model,
            dim=self._dim,
            include_current_turn=include_current_turn,
            exclude_source_ids=exclude_source_ids,
        )

    async def index_and_retrieve(
        self,
        *,
        user_id: str,
        chunks: Sequence[UserMemoryChunk] | Sequence[MemoryChunk],
        query_text: str,
        days_back: int = 14,
        top_k: int = 6,
    ) -> IndexResult:
        upsert_result = await self.upsert_chunks(user_id=user_id, chunks=chunks)
        retrieved = await self.retrieve_relevant(
            user_id=user_id,
            query_text=query_text,
            days_back=days_back,
            top_k=top_k,
            include_current_turn=False,
            exclude_source_ids=None,
        )
        return IndexResult(
            retrieved_memories=retrieved,
            indexed_count=upsert_result.indexed_count,
            reembedded_count=upsert_result.reembedded_count,
            skipped_count=upsert_result.skipped_count,
            used_embedding_provider=upsert_result.used_embedding_provider,
        )

    def _normalize_chunk(self, chunk: UserMemoryChunk | MemoryChunk) -> MemoryChunk:
        if isinstance(chunk, MemoryChunk):
            return chunk
        return MemoryChunk(
            id=chunk.id,
            user_id=chunk.user_id,
            date=chunk.date,
            source_type=chunk.source_type,
            source_id=chunk.source_id,
            text=chunk.text,
            metadata=dict(chunk.metadata),
            content_hash=chunk.content_hash,
            is_current_turn=bool(chunk.is_current_turn),
            request_id=chunk.request_id,
        )

    def _provider_name(self) -> str:
        return getattr(self._embedding_service, "last_provider", "primary")


def _batched(values: Sequence[MemoryChunk], batch_size: int) -> list[list[MemoryChunk]]:
    out: list[list[MemoryChunk]] = []
    current: list[MemoryChunk] = []
    for value in values:
        current.append(value)
        if len(current) >= batch_size:
            out.append(current)
            current = []
    if current:
        out.append(current)
    return out


def _parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except Exception:
        return None


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    if length == 0:
        return 0.0
    num = sum(float(a[i]) * float(b[i]) for i in range(length))
    denom_a = sqrt(sum(float(a[i]) * float(a[i]) for i in range(length)))
    denom_b = sqrt(sum(float(b[i]) * float(b[i]) for i in range(length)))
    if denom_a <= 1e-9 or denom_b <= 1e-9:
        return 0.0
    return num / (denom_a * denom_b)
