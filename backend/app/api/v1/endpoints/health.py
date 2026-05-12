from __future__ import annotations

import re
from typing import Any

import httpx
from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

router = APIRouter(prefix="/health")
EXPECTED_EMBEDDING_DIM = 1024


@router.get("")
async def health_check(response: Response) -> dict[str, Any]:
    embedding_contract = await check_embedding_dim_contract()
    if not embedding_contract["ok"]:
        response.status_code = 503
    status = "ok" if embedding_contract["ok"] else "unhealthy"
    if embedding_contract.get("retrieval_status") == "disabled":
        status = "degraded"
    return {
        "status": status,
        "retrieval_status": embedding_contract.get("retrieval_status", "enabled"),
        "embedding_dim_contract": embedding_contract,
    }


async def assert_startup_embedding_dim_contract() -> None:
    result = await check_embedding_dim_contract()
    if not result["ok"]:
        raise RuntimeError(f"embedding_dim_contract_failed:{result}")


async def check_embedding_dim_contract() -> dict[str, Any]:
    backend_dim = settings.embeddings_dim
    result: dict[str, Any] = {
        "ok": True,
        "backend_expected_dim": backend_dim,
        "required_dim": EXPECTED_EMBEDDING_DIM,
        "bge_reported_dim": None,
        "pgvector_column_dim": None,
        "retrieval_status": "enabled" if settings.memory_retrieval_enabled else "disabled",
    }

    if not settings.memory_retrieval_enabled:
        result["skipped_reason"] = "retrieval_disabled"
        return result

    if backend_dim != EXPECTED_EMBEDDING_DIM:
        result["ok"] = False
        result["error"] = "backend_embedding_dim_mismatch"
        return result

    if (
        settings.memory_store_backend != "postgres"
        or settings.embeddings_force_fake
        or settings.embeddings_provider == "fake"
    ):
        result["skipped_reason"] = "dim_cross_check_requires_postgres_bge"
        return result

    try:
        bge_dim = await _fetch_bge_dim()
        pg_dim = await _fetch_pgvector_dim()
    except Exception as exc:
        result["ok"] = False
        result["error"] = f"dim_cross_check_error:{exc.__class__.__name__}"
        return result

    result["bge_reported_dim"] = bge_dim
    result["pgvector_column_dim"] = pg_dim
    if bge_dim != backend_dim or pg_dim != backend_dim:
        result["ok"] = False
        result["error"] = "embedding_dim_contract_mismatch"
    return result


async def _fetch_bge_dim() -> int:
    endpoint = f"{settings.embeddings_bge_base_url.rstrip('/')}/{settings.embeddings_bge_endpoint.lstrip('/')}"
    headers = {"Content-Type": "application/json"}
    if settings.embeddings_api_key:
        headers["Authorization"] = f"Bearer {settings.embeddings_api_key}"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            json={"model": settings.embeddings_bge_model, "input": ["health dimension check"]},
            headers=headers,
            timeout=5.0,
        )
        response.raise_for_status()
        payload = response.json()
    return int(payload["dim"])


async def _fetch_pgvector_dim() -> int:
    engine = create_async_engine(settings.db_dsn)
    try:
        async with engine.connect() as connection:
            column_type = (
                await connection.execute(
                    text(
                        """
                        SELECT format_type(a.atttypid, a.atttypmod) AS column_type
                        FROM pg_attribute a
                        INNER JOIN pg_class c ON c.oid = a.attrelid
                        WHERE c.relname = 'user_memory_embeddings'
                          AND pg_table_is_visible(c.oid)
                          AND a.attname = 'embedding'
                          AND a.attnum > 0
                          AND NOT a.attisdropped
                        """
                    )
                )
            ).scalar_one()
    finally:
        await engine.dispose()

    match = re.fullmatch(r"vector\((\d+)\)", str(column_type))
    if match is None:
        raise RuntimeError(f"unexpected_pgvector_column_type:{column_type}")
    return int(match.group(1))
