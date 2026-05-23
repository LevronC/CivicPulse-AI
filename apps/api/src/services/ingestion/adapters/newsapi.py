from __future__ import annotations

"""
NewsAPI source adapter.

Purpose:
  Fetch article search results from NewsAPI and normalize them to ArticleCreate.

Responsibilities:
  Keep NewsAPI endpoint parameters, credentials, and payload mapping isolated
  from ingestion orchestration and route handlers.

Extension points:
  Add additional NewsAPI endpoints or query profiles by adding configuration
  fields and small mapping helpers in this module.

Future replacement strategy:
  Replace NewsAPI with another news search provider by adding a new adapter that
  implements SourceAdapter; no IngestionService changes are required.
"""

from dataclasses import dataclass

from src.contracts.articles import ArticleCreate
from src.logging import get_logger
from src.services.ingestion.http_client import HttpClient
from src.services.ingestion.normalization import build_article, parse_provider_datetime
from src.services.ingestion.source_adapter import SourceAdapter
from src.services.ingestion.types import (
    RateLimitContext,
    RateLimiter,
    SourceMetadata,
    SourceNormalizationError,
)

logger = get_logger("ingestion.newsapi")


@dataclass(frozen=True)
class NewsApiConfig:
    api_key: str
    query: str = "politics OR conflict OR protest OR election"
    language: str = "en"
    page_size: int = 50
    endpoint: str = "https://newsapi.org/v2/everything"


class NewsApiSourceAdapter(SourceAdapter):
    """Adapter for NewsAPI everything-search responses."""

    def __init__(
        self,
        *,
        config: NewsApiConfig,
        http_client: HttpClient,
        rate_limiter: RateLimiter,
    ) -> None:
        self._config = config
        self._http_client = http_client
        self._rate_limiter = rate_limiter

    @property
    def source_name(self) -> str:
        return "newsapi"

    @property
    def metadata(self) -> SourceMetadata:
        return SourceMetadata(
            provider="newsapi",
            display_name="NewsAPI",
            homepage_url="https://newsapi.org",
        )

    def fetch(self) -> list[ArticleCreate]:
        self._rate_limiter.wait(
            RateLimitContext(provider=self.source_name, operation="everything")
        )
        payload = self._http_client.get_json(
            self._config.endpoint,
            params={
                "q": self._config.query,
                "language": self._config.language,
                "sortBy": "publishedAt",
                "pageSize": self._config.page_size,
                "apiKey": self._config.api_key,
            },
        )
        articles = payload.get("articles", [])
        if not isinstance(articles, list):
            logger.warning("NewsAPI returned invalid articles payload")
            return []

        normalized: list[ArticleCreate] = []
        for item in articles:
            if not isinstance(item, dict):
                continue
            try:
                normalized.append(
                    build_article(
                        source=self.source_name,
                        url=item.get("url"),
                        title=item.get("title"),
                        body=item.get("content") or item.get("description"),
                        published_at=parse_provider_datetime(item.get("publishedAt")),
                        language=self._config.language,
                    )
                )
            except SourceNormalizationError as exc:
                logger.warning(
                    "NewsAPI article skipped",
                    extra={"extra_data": {"url": item.get("url"), "error": str(exc)}},
                )
        return normalized
