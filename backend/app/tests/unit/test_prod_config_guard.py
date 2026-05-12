from app.api.deps import _validate_runtime_config, get_decision_pipeline
from app.core.config import settings


def _set_defaults() -> None:
    settings.app_env = "dev"
    settings.memory_store_backend = "in_memory"
    settings.embeddings_provider = "fake"
    settings.embeddings_force_fake = False
    settings.embeddings_fallback_to_fake = False
    settings.embeddings_bge_base_url = "http://bge-gateway:8080"
    settings.embeddings_bge_endpoint = "/embed"
    settings.memory_retrieval_enabled = True


def test_prod_rejects_inmemory_store() -> None:
    get_decision_pipeline.cache_clear()
    _set_defaults()
    settings.app_env = "prod"
    settings.memory_store_backend = "in_memory"
    settings.embeddings_provider = "bge_m3_http"
    try:
        try:
            get_decision_pipeline()
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "memory_store_backend must be 'postgres'" in str(exc)
    finally:
        _set_defaults()
        get_decision_pipeline.cache_clear()


def test_prod_rejects_fake_embeddings() -> None:
    get_decision_pipeline.cache_clear()
    _set_defaults()
    settings.app_env = "prod"
    settings.memory_store_backend = "postgres"
    settings.embeddings_provider = "fake"
    try:
        try:
            get_decision_pipeline()
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "embeddings_provider must be 'bge_m3_http'" in str(exc)
    finally:
        _set_defaults()
        get_decision_pipeline.cache_clear()


def test_prod_rejects_force_fake() -> None:
    get_decision_pipeline.cache_clear()
    _set_defaults()
    settings.app_env = "prod"
    settings.memory_store_backend = "postgres"
    settings.embeddings_provider = "bge_m3_http"
    settings.embeddings_force_fake = True
    try:
        try:
            get_decision_pipeline()
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "embeddings_force_fake must be false" in str(exc)
    finally:
        _set_defaults()
        get_decision_pipeline.cache_clear()


def test_prod_rejects_missing_bge_endpoint() -> None:
    get_decision_pipeline.cache_clear()
    _set_defaults()
    settings.app_env = "prod"
    settings.memory_store_backend = "postgres"
    settings.embeddings_provider = "bge_m3_http"
    settings.embeddings_bge_endpoint = ""
    try:
        try:
            get_decision_pipeline()
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "BGE HTTP provider configuration is missing" in str(exc)
    finally:
        _set_defaults()
        get_decision_pipeline.cache_clear()


def test_prod_retrieval_disabled_allows_missing_bge_endpoint() -> None:
    get_decision_pipeline.cache_clear()
    _set_defaults()
    settings.app_env = "prod"
    settings.memory_store_backend = "postgres"
    settings.embeddings_provider = "bge_m3_http"
    settings.embeddings_bge_endpoint = ""
    settings.memory_retrieval_enabled = False
    try:
        _validate_runtime_config()
    finally:
        _set_defaults()
        get_decision_pipeline.cache_clear()
