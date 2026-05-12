import asyncio

from app.services.context.embedding_service import FakeEmbeddingService, FallbackEmbeddingService


class _AlwaysFailEmbeddingService:
    async def embed_texts(self, texts):
        raise RuntimeError("boom")

    async def embed_query(self, text):
        raise RuntimeError("boom")


def test_fallback_embedding_service_uses_local_provider_on_error() -> None:
    fallback = FakeEmbeddingService(dim=16)
    service = FallbackEmbeddingService(
        primary=_AlwaysFailEmbeddingService(),
        fallback=fallback,
        use_fallback_on_error=True,
    )
    vectors = asyncio.run(service.embed_texts(["hello", "world"]))
    query = asyncio.run(service.embed_query("hello"))

    assert len(vectors) == 2
    assert len(vectors[0]) == 16
    assert len(query) == 16
    assert service.last_provider == "fallback"
