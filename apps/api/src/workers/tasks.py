from __future__ import annotations

"""
Concrete background task implementations.

When GRAPH_MODE is enabled, event rebuild tasks delegate to the
EventGraphService instead of the legacy batch EventBuilder.
"""

from src.config import get_settings
from src.events.bus import get_event_bus
from src.logging import get_logger
from src.repositories.article_repo import ArticleRepository
from src.repositories.event_repo import EventRepository
from src.repositories.graph_repo import GraphRepository
from src.services.enrichment import EnrichmentPipeline, get_model_manager
from src.services.enrichment.stages import (
    EmbeddingStageV2,
    EntityStageV2,
    SentimentStageV2,
    SummarizationStageV2,
    TopicStageV2,
)
from src.services.events import EventBuilder
from src.services.graph import EventGraphService
from src.workers.executor import TaskResult, TaskStatus

logger = get_logger("workers.tasks")


def _graph_service(
    article_repo: ArticleRepository,
    event_repo: EventRepository,
) -> EventGraphService:
    return EventGraphService(
        article_repo=article_repo,
        event_repo=event_repo,
        graph_repo=GraphRepository(event_repo._session),
    )


class EnrichmentTask:
    """Background task: enrich all pending articles."""

    def __init__(self, article_repo: ArticleRepository) -> None:
        self._repo = article_repo

    @property
    def name(self) -> str:
        return "enrichment"

    def run(self) -> TaskResult:
        manager = get_model_manager()
        stages = [
            SummarizationStageV2(manager),
            TopicStageV2(manager),
            SentimentStageV2(manager),
            EntityStageV2(manager),
            EmbeddingStageV2(manager),
        ]
        pipeline = EnrichmentPipeline(repo=self._repo, stages=stages)
        stats = pipeline.enrich_pending()

        data = {
            "processed": stats.processed,
            "succeeded": stats.succeeded,
            "partial": stats.partial,
            "failed": stats.failed,
        }

        if stats.processed > 0:
            get_event_bus().publish("enrichment.complete", data)
            if get_settings().graph.graph_mode:
                graph = _graph_service(
                    self._repo,
                    EventRepository(self._repo._session),
                )
                graph_result = graph.process_unlinked_articles(limit=stats.processed)
                projection = graph.reconcile_projection()
                data["graph"] = graph_result.model_dump()
                data["projection"] = {
                    "orphans_removed": projection.orphans_removed,
                    "graph_event_count": projection.graph_event_count,
                }

        return TaskResult(status=TaskStatus.COMPLETED, data=data)


class RebuildTask:
    """Background task: sync event graph and reconcile SQL projection."""

    def __init__(
        self,
        article_repo: ArticleRepository,
        event_repo: EventRepository,
    ) -> None:
        self._article_repo = article_repo
        self._event_repo = event_repo

    @property
    def name(self) -> str:
        return "rebuild"

    def run(self) -> TaskResult:
        if get_settings().graph.graph_mode:
            service = _graph_service(self._article_repo, self._event_repo)
            graph_result = service.process_unlinked_articles(limit=500)
            projection = service.reconcile_projection()
            data = {
                "mode": "graph",
                "graph": graph_result.model_dump(),
                "projection": {
                    "orphans_removed": projection.orphans_removed,
                    "graph_event_count": projection.graph_event_count,
                },
            }
            get_event_bus().publish("graph.sync.complete", data)
            return TaskResult(status=TaskStatus.COMPLETED, data=data)

        builder = EventBuilder(
            article_repo=self._article_repo,
            event_repo=self._event_repo,
        )
        result = builder.rebuild()
        data = {
            "mode": "batch",
            "events_created": result.events_created,
            "articles_clustered": result.articles_clustered,
            "clusters_formed": result.clusters_formed,
        }
        if result.events_created > 0:
            get_event_bus().publish("rebuild.complete", data)
        return TaskResult(status=TaskStatus.COMPLETED, data=data)


class FullPipelineTask:
    """
    Background task: ingest -> enrich -> graph sync in a single job.
    """

    def __init__(
        self,
        article_repo: ArticleRepository,
        event_repo: EventRepository,
    ) -> None:
        self._article_repo = article_repo
        self._event_repo = event_repo

    @property
    def name(self) -> str:
        return "full_pipeline"

    def run(self) -> TaskResult:
        enrich_task = EnrichmentTask(self._article_repo)
        enrich_result = enrich_task.run()

        rebuild_task = RebuildTask(self._article_repo, self._event_repo)
        rebuild_result = rebuild_task.run()

        return TaskResult(
            status=TaskStatus.COMPLETED,
            data={
                "enrichment": enrich_result.data,
                "rebuild": rebuild_result.data,
            },
        )
