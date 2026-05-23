"""Ingestion route — triggers a source fetch + dedupe + persist cycle."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config import get_settings
from src.events.bus import get_event_bus
from src.middleware.auth import require_api_key
from src.repositories.article_repo import ArticleRepository
from src.repositories.database import DatabaseSession
from src.services.ingestion import IngestionService, build_source_adapters

router = APIRouter(tags=["ingestion"])


@router.post("/ingest", dependencies=[Depends(require_api_key)])
def ingest(session: Session = Depends(DatabaseSession)) -> dict:
    repo = ArticleRepository(session)
    service = IngestionService(
        repo=repo,
        sources=build_source_adapters(get_settings()),
    )
    result = service.run()

    if result.accepted > 0:
        get_event_bus().publish("ingestion.complete", {
            "accepted": result.accepted,
            "deduplicated": result.deduplicated,
            "total_articles": repo.count(),
        })

    return {
        "fetched": result.fetched,
        "accepted": result.accepted,
        "deduplicated": result.deduplicated,
        "failed": result.failed,
        "total_articles": repo.count(),
    }
