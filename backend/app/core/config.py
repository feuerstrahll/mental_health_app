from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Mental Health Backend"
    app_env: str = "dev"
    app_debug: bool = True

    db_dsn: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/mental_health"

    qwen_enabled: bool = True
    qwen_provider: str = "freeqwenapi"
    qwen_base_url: str = "http://qwen:3264/api"
    qwen_api_key: str | None = None
    qwen_model: str = "qwen3.5-27b"
    qwen_timeout_seconds: float = 20.0
    qwen_max_retries: int = 1
    qwen_temperature: float = 0.3
    qwen_max_completion_tokens: int = Field(
        350,
        validation_alias=AliasChoices("QWEN_MAX_COMPLETION_TOKENS", "QWEN_MAX_TOKENS"),
    )
    qwen_max_response_chars: int = 1000
    qwen_debug_return_raw: bool = False

    @property
    def qwen_max_tokens(self) -> int:
        return self.qwen_max_completion_tokens

    # Context-first memory retrieval settings
    memory_retrieval_enabled: bool = True
    context_window_days: int = 14
    context_retrieval_top_k: int = 6

    # Embeddings
    embeddings_provider: str = "bge_m3_http"  # bge_m3_http | fake
    embeddings_bge_base_url: str = "http://bge-gateway:8001"
    embeddings_bge_endpoint: str = "/embed"
    embeddings_bge_model: str = "BAAI/bge-m3"
    embeddings_api_key: str = ""
    embeddings_dim: int = 1024
    embeddings_batch_size: int = 24
    embeddings_fallback_to_fake: bool = False
    embeddings_force_fake: bool = False
    memory_store_backend: str = "in_memory"  # in_memory | postgres

    # Logging/privacy
    strict_sensitive_logging: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
