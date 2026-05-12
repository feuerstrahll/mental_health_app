from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.llm.prompt_builder import PromptBuilder
from app.llm.qwen_client import OpenAICompatibleQwenClient
from app.llm.response_composer import build_default_qwen_response_service
from app.repositories.postgres.chat_repository import PostgresChatMessageRepository
from app.repositories.postgres.daily_comment_repository import PostgresDailyCommentRepository
from app.repositories.postgres.memory_store import PostgresMemoryChunkStore, PostgresMemoryEmbeddingStore
from app.repositories.postgres.session import get_async_sessionmaker as _get_async_sessionmaker
from app.repositories.postgres.wellbeing_repository import PostgresWellbeingRepository
from app.services.context.embedding_service import (
    BgeM3HttpEmbeddingService,
    EmbeddingGatewayConfig,
    FakeEmbeddingService,
    FallbackEmbeddingService,
)
from app.services.context.memory_index_service import InMemoryChunkStore, InMemoryEmbeddingStore, MemoryIndexService
from app.services.context.practice_retriever import PracticeRetriever
from app.services.context.recent_context_summary_service import RecentContextSummaryService
from app.services.context.user_memory_chunk_service import UserMemoryChunkService
from app.services.ml.support_model import ContextAssessorService
from app.services.orchestration.decision_pipeline import (
    DecisionPipeline,
    SafetyGateService,
)


def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return _get_async_sessionmaker()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async_session = get_async_sessionmaker()
    async with async_session() as session:
        yield session


@lru_cache(maxsize=1)
def get_decision_pipeline() -> DecisionPipeline:
    _validate_runtime_config()

    session_maker = get_async_sessionmaker() if settings.memory_store_backend == "postgres" else None
    memory_index_service = _build_memory_index_service(session_maker=session_maker)
    repositories = _build_repositories(session_maker=session_maker)

    qwen_client = OpenAICompatibleQwenClient(
        enabled=settings.qwen_enabled,
        base_url=settings.qwen_base_url,
        api_key=settings.qwen_api_key,
        model=settings.qwen_model,
        timeout_seconds=settings.qwen_timeout_seconds,
        temperature=settings.qwen_temperature,
        max_completion_tokens=settings.qwen_max_completion_tokens,
        max_retries=settings.qwen_max_retries,
    )
    qwen_response_service = build_default_qwen_response_service(
        model_client=qwen_client,
        prompt_builder=PromptBuilder(),
        timeout_seconds=settings.qwen_timeout_seconds,
        max_response_chars=settings.qwen_max_response_chars,
        include_raw_model_response=settings.qwen_debug_return_raw,
    )

    return DecisionPipeline(
        qwen_response_service=qwen_response_service,
        recent_context_summary_service=RecentContextSummaryService(),
        safety_gate_service=SafetyGateService(),
        practice_retriever=PracticeRetriever(),
        context_assessor_service=ContextAssessorService(
            model_client=qwen_client,
            timeout_seconds=settings.qwen_timeout_seconds,
            include_raw_model_response=settings.qwen_debug_return_raw,
        ),
        user_memory_chunk_service=UserMemoryChunkService(),
        memory_index_service=memory_index_service,
        wellbeing_repository=repositories["wellbeing"],
        conversation_repository=repositories["conversation"],
        daily_comment_repository=repositories["daily_comment"],
        app_debug=settings.app_debug,
        strict_sensitive_logging=settings.strict_sensitive_logging,
        recent_entries_limit=settings.context_window_days,
        retrieved_memories_limit=settings.context_retrieval_top_k,
        memory_retrieval_enabled=settings.memory_retrieval_enabled,
    )


def _validate_runtime_config() -> None:
    if settings.app_env == "prod":
        if settings.memory_store_backend != "postgres":
            raise RuntimeError("memory_store_backend must be 'postgres' in prod")
        if settings.embeddings_provider != "bge_m3_http":
            raise RuntimeError("embeddings_provider must be 'bge_m3_http' in prod")
        if settings.embeddings_force_fake:
            raise RuntimeError("embeddings_force_fake must be false in prod")

    if (
        settings.memory_retrieval_enabled
        and settings.embeddings_provider == "bge_m3_http"
        and not settings.embeddings_force_fake
    ):
        if not settings.embeddings_bge_base_url.strip() or not settings.embeddings_bge_endpoint.strip():
            raise RuntimeError("BGE HTTP provider configuration is missing")

    if settings.memory_store_backend not in {"in_memory", "postgres"}:
        raise RuntimeError("memory_store_backend must be 'in_memory' or 'postgres'")

    if not isinstance(settings.memory_retrieval_enabled, bool):
        raise RuntimeError("memory_retrieval_enabled must be boolean")

    if settings.embeddings_provider not in {"bge_m3_http", "fake"}:
        raise RuntimeError("embeddings_provider must be 'bge_m3_http' or 'fake'")


def _build_memory_index_service(
    *,
    session_maker: async_sessionmaker[AsyncSession] | None,
) -> MemoryIndexService:
    embedding_service = _build_embedding_service()

    if settings.memory_store_backend == "postgres":
        if session_maker is None:
            raise RuntimeError("Postgres memory store requires a session maker")
        chunk_store = PostgresMemoryChunkStore(session_maker=session_maker)
        embedding_store = PostgresMemoryEmbeddingStore(session_maker=session_maker)
    else:
        chunk_store = InMemoryChunkStore()
        embedding_store = InMemoryEmbeddingStore()

    return MemoryIndexService(
        embedding_service=embedding_service,
        chunk_store=chunk_store,
        embedding_store=embedding_store,
        model=_embedding_model_name(),
        dim=settings.embeddings_dim,
        batch_size=settings.embeddings_batch_size,
    )


def _build_embedding_service():
    fallback = FakeEmbeddingService(dim=settings.embeddings_dim)
    if settings.embeddings_force_fake or settings.embeddings_provider == "fake":
        return fallback

    primary = BgeM3HttpEmbeddingService(
        config=EmbeddingGatewayConfig(
            base_url=settings.embeddings_bge_base_url,
            endpoint=settings.embeddings_bge_endpoint,
            model=settings.embeddings_bge_model,
            api_key=settings.embeddings_api_key,
        ),
        http_client=httpx.AsyncClient(),
    )
    return FallbackEmbeddingService(
        primary=primary,
        fallback=fallback,
        use_fallback_on_error=settings.embeddings_fallback_to_fake,
    )


def _embedding_model_name() -> str:
    if settings.embeddings_force_fake or settings.embeddings_provider == "fake":
        return "fake"
    return settings.embeddings_bge_model


def _build_repositories(
    *,
    session_maker: async_sessionmaker[AsyncSession] | None,
) -> dict[str, object | None]:
    if settings.memory_store_backend != "postgres" or session_maker is None:
        return {
            "wellbeing": None,
            "conversation": None,
            "daily_comment": None,
        }

    return {
        "wellbeing": PostgresWellbeingRepository(session_maker=session_maker),
        "conversation": PostgresChatMessageRepository(session_maker=session_maker),
        "daily_comment": PostgresDailyCommentRepository(session_maker=session_maker),
    }
