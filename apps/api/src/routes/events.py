from __future__ import annotations

"""
Event routes — list, detail, and rebuild endpoints.

When GRAPH_MODE is enabled (default), the event graph is the source
of truth. POST /events/rebuild delegates to graph sync + projection
instead of the legacy batch EventBuilder.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config import get_settings
from src.contracts.enums import SentimentLabel, Topic
from src.contracts.pagination import PaginationParams
from src.errors import NotFoundError
from src.events.bus import get_event_bus
from src.middleware.auth import require_api_key
from src.middleware.rate_limiter import RateLimiter
from src.repositories.article_repo import ArticleRepository
from src.repositories.database import DatabaseSession
from src.repositories.event_repo import EventRepository
from src.repositories.graph_repo import GraphRepository
from src.services.events import EventBuilder
from src.services.graph import EventGraphService

router = APIRouter(prefix="/events", tags=["events"])
_rate_limiter = RateLimiter()


def _graph_service(session: Session) -> EventGraphService:
    return EventGraphService(
        article_repo=ArticleRepository(session),
        event_repo=EventRepository(session),
        graph_repo=GraphRepository(session),
    )


@router.post("/rebuild", dependencies=[Depends(require_api_key)])
def rebuild_events(session: Session = Depends(DatabaseSession)) -> dict:
    settings = get_settings()

    if settings.graph.graph_mode:
        service = _graph_service(session)
        graph_result = service.process_unlinked_articles(limit=500)
        projection = service.reconcile_projection()

        if graph_result.mutations:
            bus = get_event_bus()
            for mutation in graph_result.mutations:
                bus.publish(f"graph.{mutation.mutation_type.value}", mutation.model_dump())

        return {
            "mode": "graph",
            "message": "Batch rebuild is disabled. Ran graph sync + projection instead.",
            "use_instead": "/intelligence/sync",
            "graph": graph_result.model_dump(),
            "projection": {
                "orphans_removed": projection.orphans_removed,
                "events_synced": projection.events_synced,
                "graph_event_count": projection.graph_event_count,
            },
        }

    article_repo = ArticleRepository(session)
    event_repo = EventRepository(session)
    builder = EventBuilder(article_repo=article_repo, event_repo=event_repo)
    result = builder.rebuild()

    if result.events_created > 0:
        bus = get_event_bus()
        events = event_repo.list_events(PaginationParams(offset=0, limit=100))
        for event in events.items:
            bus.publish("event.created", event.model_dump())

    return {
        "mode": "batch",
        "events_created": result.events_created,
        "articles_clustered": result.articles_clustered,
        "clusters_formed": result.clusters_formed,
    }


@router.get("")
def list_events(
    session: Session = Depends(DatabaseSession),
    topic: str | None = Query(default=None),
    sentiment: str | None = Query(default=None),
    min_impact: float = Query(default=0.0, ge=0),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    _rate_limiter.check("public-events")
    event_repo = EventRepository(session)
    settings = get_settings()

    topic_enum = Topic(topic) if topic else None
    sentiment_enum = SentimentLabel(sentiment) if sentiment else None
    pagination = PaginationParams(offset=offset, limit=limit)

    result = event_repo.list_events(
        pagination,
        topic=topic_enum,
        sentiment=sentiment_enum,
        min_impact=min_impact,
        graph_only=settings.graph.graph_mode,
    )
    return result.model_dump()


@router.get("/{event_id}")
def event_detail(
    event_id: str,
    session: Session = Depends(DatabaseSession),
) -> dict:
    _rate_limiter.check("public-events")
    event_repo = EventRepository(session)
    article_repo = ArticleRepository(session)

    event = event_repo.get_event(event_id)
    if event is None:
        raise NotFoundError("Event", event_id)

    articles = []
    for aid in event.article_ids:
        article = article_repo.get_article(aid)
        if article:
            articles.append(article.model_dump())

    return {"event": event.model_dump(), "articles": articles}
