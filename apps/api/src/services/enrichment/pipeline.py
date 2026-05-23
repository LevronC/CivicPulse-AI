from __future__ import annotations

"""
Enrichment pipeline orchestrator.

Runs all enrichment stages through the model manager abstraction,
collecting per-stage metadata (confidence, latency, provenance)
into a composite EnrichmentResult.

The pipeline is agnostic to what models run behind the stages.
Replacing heuristic backends with transformer backends is a
ModelManager configuration change — this file stays unchanged.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.contracts.articles import EnrichmentResult, StageMetadata
from src.contracts.enums import SentimentLabel, Topic
from src.logging import get_logger
from src.repositories.article_repo import ArticleRepository
from src.services.enrichment.interfaces.stage import EnrichmentStageInterface

logger = get_logger("enrichment.pipeline")


@dataclass
class PipelineStats:
    processed: int = 0
    succeeded: int = 0
    partial: int = 0
    failed: int = 0
    stage_failures: dict[str, int] = field(default_factory=dict)
    total_latency_ms: float = 0.0


class EnrichmentPipeline:
    """
    Orchestrates enrichment stages with full telemetry.

    Each article is independently enriched — failures on one
    article do not block the batch. Partial enrichment (some
    stages succeeded) is still persisted with explicit nulls
    for failed stages and per-stage metadata.
    """

    def __init__(
        self,
        repo: ArticleRepository,
        stages: list[EnrichmentStageInterface],
    ) -> None:
        self._repo = repo
        self._stages = stages

    def enrich_pending(self, batch_size: int = 50) -> PipelineStats:
        unenriched_ids = self._repo.get_unenriched_ids(limit=batch_size)
        stats = PipelineStats()

        for article_id in unenriched_ids:
            article = self._repo.get_article(article_id)
            if article is None:
                continue

            text = f"{article.title} {article.body}"
            pipeline_start = time.monotonic()
            merged: dict = {}
            stage_metadata: list[StageMetadata] = []
            failed_stages: list[str] = []
            succeeded_count = 0

            for stage in self._stages:
                try:
                    result = stage.process(text)
                    merged.update(result.outputs)
                    succeeded_count += 1
                    stage_metadata.append(StageMetadata(
                        stage_name=stage.name,
                        model_name=result.model_name,
                        model_version=result.model_version,
                        confidence=result.confidence,
                        latency_ms=round(result.latency_ms, 2),
                        timestamp=result.timestamp,
                        warnings=result.warnings,
                    ))
                    logger.info(
                        "Stage complete",
                        extra={
                            "stage": stage.name,
                            "article_id": article_id,
                            "latency_ms": round(result.latency_ms, 1),
                            "confidence": round(result.confidence, 2),
                        },
                    )
                except Exception:
                    failed_stages.append(stage.name)
                    stats.stage_failures[stage.name] = (
                        stats.stage_failures.get(stage.name, 0) + 1
                    )
                    logger.exception(
                        "Stage failed",
                        extra={"stage": stage.name, "article_id": article_id},
                    )

            pipeline_latency = (time.monotonic() - pipeline_start) * 1000

            enrichment = EnrichmentResult(
                summary=merged.get("summary"),
                topic=merged.get("topic"),
                sentiment=merged.get("sentiment"),
                entities=merged.get("entities", []),
                embedding=merged.get("embedding", []),
                total_latency_ms=round(pipeline_latency, 2),
                stage_metadata=stage_metadata,
                processed_at=datetime.now(timezone.utc),
                stages_succeeded=succeeded_count,
                stages_failed=len(failed_stages),
            )

            try:
                self._repo.save_enrichment(article_id, enrichment)
                stats.processed += 1
                stats.total_latency_ms += pipeline_latency
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

        logger.info("Pipeline batch complete", extra={"stats": stats.__dict__})
        return stats
