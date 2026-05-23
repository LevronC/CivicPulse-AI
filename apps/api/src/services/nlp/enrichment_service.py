from __future__ import annotations

"""
Enrichment orchestrator.

Runs all NLP stages sequentially on each article, collecting partial
results even when individual stages fail. Stage-level telemetry
(success/failure/latency) is emitted for every execution to support
pipeline health monitoring.

The orchestrator is agnostic to what the stages do — it only knows
the stage interface. New stages can be added or reordered without
modifying this file.
"""

import time
from dataclasses import dataclass, field

from src.contracts.articles import EnrichmentResult
from src.contracts.enums import SentimentLabel, Topic
from src.logging import get_logger
from src.repositories.article_repo import ArticleRepository
from src.services.nlp.stages import EnrichmentStage

logger = get_logger("service.enrichment")


@dataclass
class EnrichmentStats:
    processed: int = 0
    succeeded: int = 0
    partial: int = 0
    failed: int = 0
    stage_failures: dict[str, int] = field(default_factory=dict)


class EnrichmentService:
    def __init__(
        self,
        repo: ArticleRepository,
        stages: list[EnrichmentStage],
    ) -> None:
        self._repo = repo
        self._stages = stages

    def enrich_pending(self, batch_size: int = 50) -> EnrichmentStats:
        """
        Process unenriched articles through the NLP pipeline.

        Each article is independently enriched — failures on one
        article do not block the batch. Partial enrichment (some
        stages succeeded) is still persisted with explicit nulls
        for failed stages.
        """
        unenriched_ids = self._repo.get_unenriched_ids(limit=batch_size)
        stats = EnrichmentStats()

        for article_id in unenriched_ids:
            article = self._repo.get_article(article_id)
            if article is None:
                continue

            text = f"{article.title} {article.body}"
            merged: dict = {}
            stage_count = 0
            failed_stages: list[str] = []

            for stage in self._stages:
                start = time.monotonic()
                try:
                    result = stage.process(text)
                    merged.update(result)
                    stage_count += 1
                    elapsed = (time.monotonic() - start) * 1000
                    logger.info(
                        "Stage complete",
                        extra={
                            "stage": stage.name,
                            "article_id": article_id,
                            "latency_ms": round(elapsed, 1),
                        },
                    )
                except Exception:
                    failed_stages.append(stage.name)
                    stats.stage_failures[stage.name] = stats.stage_failures.get(stage.name, 0) + 1
                    logger.exception(
                        "Stage failed",
                        extra={"stage": stage.name, "article_id": article_id},
                    )

            enrichment = EnrichmentResult(
                summary=merged.get("summary"),
                topic=merged.get("topic"),
                sentiment=merged.get("sentiment"),
                entities=merged.get("entities", []),
                embedding=merged.get("embedding", []),
            )

            try:
                self._repo.save_enrichment(article_id, enrichment)
                stats.processed += 1
                if failed_stages:
                    stats.partial += 1
                else:
                    stats.succeeded += 1
            except Exception:
                stats.failed += 1
                logger.exception(
                    "Enrichment persistence failed",
                    extra={"article_id": article_id},
                )

        logger.info("Enrichment batch complete", extra={"stats": stats.__dict__})
        return stats
