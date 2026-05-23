"""
Intelligence API — global pulse, breaking stories, narrative map, entities.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.errors import NotFoundError
from src.events.bus import get_event_bus
from src.middleware.auth import require_api_key
from src.middleware.rate_limiter import RateLimiter
from src.repositories.article_repo import ArticleRepository
from src.repositories.database import DatabaseSession
from src.repositories.event_repo import EventRepository
from src.repositories.graph_repo import GraphRepository
from src.services.graph import EventGraphService

router = APIRouter(prefix="/intelligence", tags=["intelligence"])
_rate_limiter = RateLimiter()


def _graph_service(session: Session) -> EventGraphService:
    return EventGraphService(
        article_repo=ArticleRepository(session),
        event_repo=EventRepository(session),
        graph_repo=GraphRepository(session),
    )


@router.get("/pulse")
def global_pulse(
    session: Session = Depends(DatabaseSession),
    limit: int = Query(default=20, ge=1, le=100),
    window_hours: float = Query(default=24.0, ge=1, le=168),
) -> dict:
    _rate_limiter.check("public-intelligence")
    result = _graph_service(session).global_pulse(limit=limit, window_hours=window_hours)
    return result.model_dump()


@router.get("/breaking")
def breaking_stories(
    session: Session = Depends(DatabaseSession),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict:
    """Fast-growing or newly forming stories ranked by breaking score."""
    _rate_limiter.check("public-intelligence")
    items = _graph_service(session).breaking_stories(limit=limit)
    return {"items": [i.model_dump() for i in items], "count": len(items)}


@router.get("/emerging")
def emerging_events(
    session: Session = Depends(DatabaseSession),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict:
    """Alias for breaking story detection (backward compatible)."""
    _rate_limiter.check("public-intelligence")
    items = _graph_service(session).emerging_events(limit=limit)
    return {"items": [i.model_dump() for i in items], "count": len(items)}


@router.get("/narrative-map")
def narrative_map(
    session: Session = Depends(DatabaseSession),
    limit: int = Query(default=40, ge=5, le=100),
) -> dict:
    """Event nodes and related_to edges for global narrative visualization."""
    _rate_limiter.check("public-intelligence")
    return _graph_service(session).narrative_map(limit=limit).model_dump()


@router.get("/entities")
def top_entities(
    session: Session = Depends(DatabaseSession),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Most connected entities ranked by linked event count."""
    _rate_limiter.check("public-intelligence")
    items = _graph_service(session).top_entities(limit=limit)
    return {"items": [i.model_dump() for i in items], "count": len(items)}


@router.get("/events/{event_id}/evolution")
def event_evolution(
    event_id: str,
    session: Session = Depends(DatabaseSession),
) -> dict:
    _rate_limiter.check("public-intelligence")
    result = _graph_service(session).event_evolution(event_id)
    if result is None:
        raise NotFoundError("Event", event_id)
    return result.model_dump()


@router.get("/entities/{entity_name}")
def entity_intelligence(
    entity_name: str,
    session: Session = Depends(DatabaseSession),
) -> dict:
    _rate_limiter.check("public-intelligence")
    result = _graph_service(session).entity_intelligence(entity_name)
    if result is None:
        raise NotFoundError("Entity", entity_name)
    return result.model_dump()


@router.post("/strengthen-edges", dependencies=[Depends(require_api_key)])
def strengthen_edges(session: Session = Depends(DatabaseSession)) -> dict:
    """Rebuild cross-event similarity edges from active event centroids."""
    result = _graph_service(session).strengthen_similarity_edges()
    return result.model_dump()


@router.post("/sync", dependencies=[Depends(require_api_key)])
def sync_graph(
    session: Session = Depends(DatabaseSession),
    limit: int = Query(default=50, ge=1, le=500),
    bootstrap: bool = Query(default=False),
) -> dict:
    service = _graph_service(session)
    if bootstrap:
        result = service.bootstrap_from_enriched()
    else:
        result = service.process_unlinked_articles(limit=limit)

    projection = service.reconcile_projection()
    edges = service.strengthen_similarity_edges()

    if result.mutations:
        bus = get_event_bus()
        for mutation in result.mutations:
            bus.publish(f"graph.{mutation.mutation_type.value}", mutation.model_dump())

    return {
        **result.model_dump(),
        "projection": {
            "orphans_removed": projection.orphans_removed,
            "events_synced": projection.events_synced,
            "graph_event_count": projection.graph_event_count,
        },
        "edges": edges.model_dump(),
    }
