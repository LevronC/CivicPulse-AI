from __future__ import annotations

"""
GDELT source adapter.

Purpose:
  Fetch GDELT document API results and normalize them into ArticleCreate.

Responsibilities:
  Encapsulate GDELT query parameters, date parsing, and document payload shape.

Extension points:
  Add alternate modes or geographic query profiles through config fields while
  keeping SourceAdapter.fetch() unchanged.

Future replacement strategy:
  This adapter can be moved to a dedicated worker process or replaced with a
  streaming GDELT connector without changing ingestion persistence.
"""

from dataclasses import dataclass

from src.contracts.articles import ArticleCreate
from src.logging import get_logger
from src.services.ingestion.http_client import HttpClient
from src.services.ingestion.normalization import build_article, parse_gdelt_datetime
from src.services.ingestion.source_adapter import SourceAdapter
from src.services.ingestion.types import (
    RateLimitContext,
    RateLimiter,
    SourceMetadata,
    SourceNormalizationError,
)

logger = get_logger("ingestion.gdelt")


@dataclass(frozen=True)
class GdeltConfig:
    query: str = "protest OR election OR conflict OR disaster"
    max_records: int = 50
    endpoint: str = "https://api.gdeltproject.org/api/v2/doc/doc"


class GdeltSourceAdapter(SourceAdapter):
    """Adapter for GDELT DOC 2.0 article-list responses."""

    def __init__(
        self,
        *,
        config: GdeltConfig,
        http_client: HttpClient,
        rate_limiter: RateLimiter,
    ) -> None:
        self._config = config
        self._http_client = http_client
        self._rate_limiter = rate_limiter

    @property
    def source_name(self) -> str:
        return "gdelt"

    @property
    def metadata(self) -> SourceMetadata:
        return SourceMetadata(
            provider="gdelt",
            display_name="GDELT",
            homepage_url="https://www.gdeltproject.org",
        )

    def fetch(self) -> list[ArticleCreate]:
        self._rate_limiter.wait(
            RateLimitContext(provider=self.source_name, operation="doc_articles")
        )
        payload = self._http_client.get_json(
            self._config.endpoint,
            params={
                "query": self._config.query,
                "mode": "ArtList",
                "format": "json",
                "maxrecords": self._config.max_records,
                "sort": "HybridRel",
            },
        )
        documents = payload.get("articles", [])
        if not isinstance(documents, list):
            logger.warning("GDELT returned invalid articles payload")
            return []

        normalized: list[ArticleCreate] = []
        for item in documents:
            if not isinstance(item, dict):
                continue
            try:
                normalized.append(
                    build_article(
                        source=self.source_name,
                        url=item.get("url"),
                        title=item.get("title"),
                        body=item.get("seendate") and item.get("title"),
                        published_at=parse_gdelt_datetime(item.get("seendate")),
                        language=item.get("language") or "en",
                    )
                )
            except SourceNormalizationError as exc:
                logger.warning(
                    "GDELT article skipped",
                    extra={"extra_data": {"url": item.get("url"), "error": str(exc)}},
                )
        return normalized
