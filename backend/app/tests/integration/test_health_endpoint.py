from fastapi.testclient import TestClient
import pytest

from app.api.v1.endpoints import health
from app.core.config import settings
from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_endpoint_reports_embedding_dim_mismatch(monkeypatch) -> None:
    async def fake_bge_dim() -> int:
        return 768

    async def fake_pgvector_dim() -> int:
        return 1024

    monkeypatch.setattr(settings, "memory_store_backend", "postgres")
    monkeypatch.setattr(settings, "embeddings_provider", "bge_m3_http")
    monkeypatch.setattr(settings, "embeddings_force_fake", False)
    monkeypatch.setattr(settings, "embeddings_dim", 1024)
    monkeypatch.setattr(settings, "memory_retrieval_enabled", True)
    monkeypatch.setattr(health, "_fetch_bge_dim", fake_bge_dim)
    monkeypatch.setattr(health, "_fetch_pgvector_dim", fake_pgvector_dim)

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "unhealthy"
    assert payload["embedding_dim_contract"]["backend_expected_dim"] == 1024
    assert payload["embedding_dim_contract"]["bge_reported_dim"] == 768
    assert payload["embedding_dim_contract"]["pgvector_column_dim"] == 1024
    assert payload["embedding_dim_contract"]["error"] == "embedding_dim_contract_mismatch"


def test_startup_fails_fast_on_embedding_dim_mismatch(monkeypatch) -> None:
    async def fake_bge_dim() -> int:
        return 1024

    async def fake_pgvector_dim() -> int:
        return 768

    monkeypatch.setattr(settings, "memory_store_backend", "postgres")
    monkeypatch.setattr(settings, "embeddings_provider", "bge_m3_http")
    monkeypatch.setattr(settings, "embeddings_force_fake", False)
    monkeypatch.setattr(settings, "embeddings_dim", 1024)
    monkeypatch.setattr(settings, "memory_retrieval_enabled", True)
    monkeypatch.setattr(health, "_fetch_bge_dim", fake_bge_dim)
    monkeypatch.setattr(health, "_fetch_pgvector_dim", fake_pgvector_dim)

    with pytest.raises(RuntimeError, match="embedding_dim_contract_failed"):
        with TestClient(app):
            pass


def test_retrieval_disabled_health_is_degraded_without_dim_checks(monkeypatch) -> None:
    async def fail_if_called() -> int:
        raise AssertionError("dim check should be skipped when retrieval is disabled")

    monkeypatch.setattr(settings, "memory_store_backend", "postgres")
    monkeypatch.setattr(settings, "embeddings_provider", "bge_m3_http")
    monkeypatch.setattr(settings, "embeddings_force_fake", False)
    monkeypatch.setattr(settings, "embeddings_dim", 1024)
    monkeypatch.setattr(settings, "memory_retrieval_enabled", False)
    monkeypatch.setattr(health, "_fetch_bge_dim", fail_if_called)
    monkeypatch.setattr(health, "_fetch_pgvector_dim", fail_if_called)

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["retrieval_status"] == "disabled"
    assert payload["embedding_dim_contract"]["skipped_reason"] == "retrieval_disabled"
