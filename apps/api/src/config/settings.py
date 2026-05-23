from __future__ import annotations

"""
Typed configuration with validation.

All environment variables are validated at startup. Missing
required values cause a clear error before any service starts,
preventing runtime surprises from misconfigured deployments.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class DatabaseSettings(BaseSettings):
    url: str = Field(
        default="postgresql+psycopg://civicpulse:civicpulse@localhost:5432/civicpulse",
        alias="DATABASE_URL",
    )
    pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    pool_overflow: int = Field(default=10, alias="DB_POOL_OVERFLOW")


class RedisSettings(BaseSettings):
    url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")


class NlpSettings(BaseSettings):
    """
    NLP provider configuration. Heuristic-based enrichment is the default.
    When a HuggingFace model name is set, the pipeline switches to
    model-based inference. This allows hot-swapping providers without
    touching business logic.
    """

    summary_model: str = Field(default="heuristic", alias="HF_MODEL_SUMMARY")
    classifier_model: str = Field(default="heuristic", alias="HF_MODEL_CLASSIFIER")
    sentiment_model: str = Field(default="heuristic", alias="HF_MODEL_SENTIMENT")
    ner_model: str = Field(default="heuristic", alias="HF_MODEL_NER")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    embedding_dims: int = Field(default=384, alias="EMBEDDING_DIMS")


class SourceSettings(BaseSettings):
    """
    Source provider configuration.

    Provider names map to SourceAdapter implementations in the ingestion
    registry. Missing credentials disable only that provider; the registry can
    still build other sources or fall back to the mock adapter for local dev.
    """

    enabled_providers: list[str] = Field(default=["mock"], alias="SOURCE_PROVIDERS")
    rss_feeds: list[str] = Field(default=[], alias="RSS_FEEDS")
    newsapi_api_key: str | None = Field(default=None, alias="NEWSAPI_API_KEY")
    newsapi_query: str = Field(
        default="politics OR conflict OR protest OR election",
        alias="NEWSAPI_QUERY",
    )
    newsapi_language: str = Field(default="en", alias="NEWSAPI_LANGUAGE")
    gdelt_query: str = Field(
        default="protest OR election OR conflict OR disaster",
        alias="GDELT_QUERY",
    )
    provider_page_size: int = Field(default=50, alias="SOURCE_PROVIDER_PAGE_SIZE")
    request_timeout_seconds: float = Field(default=10.0, alias="SOURCE_TIMEOUT_SECONDS")
    retry_attempts: int = Field(default=3, alias="SOURCE_RETRY_ATTEMPTS")
    retry_backoff_seconds: float = Field(default=0.25, alias="SOURCE_RETRY_BACKOFF_SECONDS")

    model_config = {
        "populate_by_name": True,
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


class GraphSettings(BaseSettings):
    """
    Event graph configuration.

    When graph_mode is enabled, EventGraphService is the sole writer
    of event state. The legacy batch rebuild path is disabled and
    the events table is treated as a materialized projection.
    """

    graph_mode: bool = Field(default=True, alias="GRAPH_MODE")
    attach_threshold: float = Field(default=0.40, alias="GRAPH_ATTACH_THRESHOLD")
    merge_threshold: float = Field(default=0.72, alias="GRAPH_MERGE_THRESHOLD")
    stale_hours: float = Field(default=72.0, alias="GRAPH_STALE_HOURS")

    model_config = {
        "populate_by_name": True,
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


class ApiSettings(BaseSettings):
    api_key: str = Field(default="dev-api-key", alias="API_KEY")
    rate_limit_per_min: int = Field(default=60, alias="RATE_LIMIT_PER_MIN")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        alias="CORS_ORIGINS",
    )


class Settings(BaseSettings):
    """Root configuration aggregating all subsystem settings."""

    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    db: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    nlp: NlpSettings = NlpSettings()
    sources: SourceSettings = SourceSettings()
    graph: GraphSettings = GraphSettings()
    api: ApiSettings = ApiSettings()

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
