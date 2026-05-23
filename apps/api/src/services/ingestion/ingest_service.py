from __future__ import annotations

"""
Ingestion orchestrator.

Coordinates source fetch -> deduplication -> persistence.
The service is stateless — all state lives in the repository.
This separation allows testing ingestion logic without a database
by injecting a mock repository.
"""

from dataclasses import dataclass

from src.contracts.articles import ArticleCreate
from src.logging import get_logger
from src.repositories.article_repo import ArticleRepository
from src.services.ingestion.dedupe import generate_article_id
from src.services.ingestion.source_adapter import SourceAdapter

logger = get_logger("service.ingestion")


@dataclass
class IngestionResult:
    fetched: int
    accepted: int
    deduplicated: int
    failed: int


class IngestionService:
    def __init__(self, repo: ArticleRepository, sources: list[SourceAdapter]) -> None:
        self._repo = repo
        self._sources = sources

    def run(self) -> IngestionResult:
        """
        Execute one ingestion cycle across all configured sources.

        Each article is independently deduped and persisted — a failure
        on one article does not block others. Failed articles are logged
        with enough context for dead-letter replay.
        """
        all_articles: list[ArticleCreate] = []
        for source in self._sources:
            try:
                batch = source.fetch()
                all_articles.extend(batch)
                logger.info(
                    "Source fetch complete",
                    extra={"source": source.source_name, "count": len(batch)},
                )
            except Exception:
                logger.exception("Source fetch failed", extra={"source": source.source_name})

        accepted = 0
        deduplicated = 0
        failed = 0

        for article in all_articles:
            try:
                article_id = generate_article_id(article.url, article.title)
                inserted = self._repo.insert_article(article_id, article.model_dump())
                if inserted:
                    accepted += 1
                else:
                    deduplicated += 1
            except Exception:
                failed += 1
                logger.exception(
                    "Article persistence failed",
                    extra={"url": article.url, "title": article.title},
                )

        result = IngestionResult(
            fetched=len(all_articles),
            accepted=accepted,
            deduplicated=deduplicated,
            failed=failed,
        )
        logger.info("Ingestion cycle complete", extra={"result": result.__dict__})
        return result
