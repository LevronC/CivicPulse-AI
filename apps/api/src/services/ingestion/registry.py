from __future__ import annotations

"""
Provider registry for ingestion source adapters.

Purpose:
  Build configured SourceAdapter instances from typed settings while keeping
  provider-selection logic out of route handlers and ingestion orchestration.

Responsibilities:
  Validate provider prerequisites, create shared infrastructure dependencies,
  and return adapters that all implement the same SourceAdapter contract.

Extension points:
  Register new providers by adding one small factory branch here and a focused
  adapter module under ingestion/adapters.

Future replacement strategy:
  This registry can evolve into a dependency-injection container or worker
  bootstrap module without changing IngestionService.
"""

from src.config.settings import Settings
from src.logging import get_logger
from src.services.ingestion.adapters import (
    GdeltConfig,
    GdeltSourceAdapter,
    NewsApiConfig,
    NewsApiSourceAdapter,
    RssSourceAdapter,
)
from src.services.ingestion.http_client import HttpClient, RequestHttpClient
from src.services.ingestion.source_adapter import MockSourceAdapter, SourceAdapter
from src.services.ingestion.types import NoopRateLimiter, RateLimiter, RetryPolicy

logger = get_logger("ingestion.registry")


def build_source_adapters(
    settings: Settings,
    *,
    http_client: HttpClient | None = None,
    rate_limiter: RateLimiter | None = None,
) -> list[SourceAdapter]:
    """Build source adapters enabled by deployment configuration."""

    sources = settings.sources
    retry_policy = RetryPolicy(
        attempts=sources.retry_attempts,
        backoff_seconds=sources.retry_backoff_seconds,
        timeout_seconds=sources.request_timeout_seconds,
    )
    client = http_client or RequestHttpClient(retry_policy=retry_policy)
    limiter = rate_limiter or NoopRateLimiter()
    enabled = {provider.lower().strip() for provider in sources.enabled_providers}

    adapters: list[SourceAdapter] = []

    if "rss" in enabled:
        if sources.rss_feeds:
            adapters.append(
                RssSourceAdapter(
                    feed_urls=sources.rss_feeds,
                    http_client=client,
                    rate_limiter=limiter,
                )
            )
        else:
            logger.warning("RSS provider enabled without RSS_FEEDS")

    if "newsapi" in enabled:
        if sources.newsapi_api_key:
            adapters.append(
                NewsApiSourceAdapter(
                    config=NewsApiConfig(
                        api_key=sources.newsapi_api_key,
                        query=sources.newsapi_query,
                        language=sources.newsapi_language,
                        page_size=sources.provider_page_size,
                    ),
                    http_client=client,
                    rate_limiter=limiter,
                )
            )
        else:
            logger.warning("NewsAPI provider enabled without NEWSAPI_API_KEY")

    if "gdelt" in enabled:
        adapters.append(
            GdeltSourceAdapter(
                config=GdeltConfig(
                    query=sources.gdelt_query,
                    max_records=sources.provider_page_size,
                ),
                http_client=client,
                rate_limiter=limiter,
            )
        )

    if "mock" in enabled or not adapters:
        adapters.append(MockSourceAdapter())

    logger.info(
        "Source adapters built",
        extra={"extra_data": {"providers": [adapter.source_name for adapter in adapters]}},
    )
    return adapters
