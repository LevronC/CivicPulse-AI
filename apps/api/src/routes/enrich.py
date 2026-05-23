"""Enrichment route — processes unenriched articles through the NLP pipeline."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.events.bus import get_event_bus
from src.middleware.auth import require_api_key
from src.repositories.article_repo import ArticleRepository
from src.repositories.database import DatabaseSession
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
from src.services.graph import EventGraphService

router = APIRouter(tags=["enrichment"])


@router.post("/enrich", dependencies=[Depends(require_api_key)])
def enrich(session: Session = Depends(DatabaseSession)) -> dict:
    repo = ArticleRepository(session)
    manager = get_model_manager()
    stages = [
        SummarizationStageV2(manager),
        TopicStageV2(manager),
        SentimentStageV2(manager),
        EntityStageV2(manager),
        EmbeddingStageV2(manager),
    ]
    pipeline = EnrichmentPipeline(repo=repo, stages=stages)
    stats = pipeline.enrich_pending()

    graph_result = None
    if stats.processed > 0:
        graph_service = EventGraphService(
            article_repo=repo,
            event_repo=EventRepository(session),
            graph_repo=GraphRepository(session),
        )
        graph_result = graph_service.process_unlinked_articles(limit=stats.processed)
        bus = get_event_bus()
        bus.publish("enrichment.complete", {
            "processed": stats.processed,
            "succeeded": stats.succeeded,
            "partial": stats.partial,
            "total_enriched": repo.enriched_count(),
            "graph_mutations": len(graph_result.mutations),
        })
        for mutation in graph_result.mutations:
            bus.publish(f"graph.{mutation.mutation_type.value}", mutation.model_dump())

    return {
        "processed": stats.processed,
        "succeeded": stats.succeeded,
        "partial": stats.partial,
        "failed": stats.failed,
        "total_enriched": repo.enriched_count(),
        "graph": graph_result.model_dump() if graph_result else None,
    }
