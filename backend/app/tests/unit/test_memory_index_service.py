import asyncio
from datetime import date

from app.services.context.embedding_service import FakeEmbeddingService
from app.services.context.memory_index_service import InMemoryChunkStore, InMemoryEmbeddingStore, MemoryIndexService
from app.services.context.user_memory_chunk_service import UserMemoryChunk


def _chunk(*, chunk_id: str, text: str, content_hash: str) -> UserMemoryChunk:
    return UserMemoryChunk(
        id=chunk_id,
        user_id="u1",
        date=date(2026, 5, 1).isoformat(),
        source_type="checkin",
        source_id=f"s:{chunk_id}",
        text=text,
        metadata={},
        content_hash=content_hash,
    )


def test_content_hash_skip_reembed() -> None:
    store = InMemoryEmbeddingStore()
    service = MemoryIndexService(
        embedding_service=FakeEmbeddingService(dim=32),
        chunk_store=InMemoryChunkStore(),
        embedding_store=store,
        model="fake",
        dim=32,
        batch_size=8,
    )
    chunks = [
        _chunk(chunk_id="a", text="sleep was short", content_hash="h1"),
        _chunk(chunk_id="b", text="felt isolated", content_hash="h2"),
    ]

    first = asyncio.run(service.index_and_retrieve(user_id="u1", chunks=chunks, query_text="sleep", days_back=14, top_k=3))
    second = asyncio.run(service.index_and_retrieve(user_id="u1", chunks=chunks, query_text="sleep", days_back=14, top_k=3))
    third = asyncio.run(
        service.index_and_retrieve(
            user_id="u1",
            chunks=[_chunk(chunk_id="a", text="sleep improved", content_hash="h3"), chunks[1]],
            query_text="sleep",
            days_back=14,
            top_k=3,
        )
    )

    assert first.reembedded_count == 2
    assert second.reembedded_count == 0
    assert second.skipped_count == 2
    assert third.reembedded_count == 1


def test_current_turn_chunks_excluded_by_default() -> None:
    store = InMemoryEmbeddingStore()
    service = MemoryIndexService(
        embedding_service=FakeEmbeddingService(dim=16),
        chunk_store=InMemoryChunkStore(),
        embedding_store=store,
        model="fake",
        dim=16,
        batch_size=8,
    )
    current_turn_chunk = UserMemoryChunk(
        id="ct1",
        user_id="u1",
        date=date(2026, 5, 1).isoformat(),
        source_type="chat_message",
        source_id="chat:ct1",
        text="Date: 2026-05-01. I feel anxious now.",
        metadata={},
        content_hash="ct_hash",
        is_current_turn=True,
        request_id="req_1",
    )
    asyncio.run(service.upsert_chunks(user_id="u1", chunks=[current_turn_chunk]))
    rows = asyncio.run(service.retrieve_relevant(user_id="u1", query_text="anxious", top_k=4))
    assert rows == []
