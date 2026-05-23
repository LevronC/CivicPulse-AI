"""Task management route — submit and monitor background work."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.middleware.auth import require_api_key
from src.repositories.article_repo import ArticleRepository
from src.repositories.database import DatabaseSession
from src.repositories.event_repo import EventRepository
from src.workers import (
    EnrichmentTask,
    FullPipelineTask,
    RebuildTask,
    get_executor,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/enrich", dependencies=[Depends(require_api_key)])
def submit_enrich_task(session: Session = Depends(DatabaseSession)) -> dict:
    """Submit enrichment as a background task."""
    repo = ArticleRepository(session)
    task_id = get_executor().submit(EnrichmentTask(repo))
    return {"task_id": task_id, "status": "submitted"}


@router.post("/rebuild", dependencies=[Depends(require_api_key)])
def submit_rebuild_task(session: Session = Depends(DatabaseSession)) -> dict:
    """Submit event rebuild as a background task."""
    article_repo = ArticleRepository(session)
    event_repo = EventRepository(session)
    task_id = get_executor().submit(RebuildTask(article_repo, event_repo))
    return {"task_id": task_id, "status": "submitted"}


@router.post("/pipeline", dependencies=[Depends(require_api_key)])
def submit_full_pipeline(session: Session = Depends(DatabaseSession)) -> dict:
    """Submit full pipeline (enrich + rebuild) as a background task."""
    article_repo = ArticleRepository(session)
    event_repo = EventRepository(session)
    task_id = get_executor().submit(FullPipelineTask(article_repo, event_repo))
    return {"task_id": task_id, "status": "submitted"}


@router.get("/{task_id}", dependencies=[Depends(require_api_key)])
def get_task_status(task_id: str) -> dict:
    record = get_executor().get_status(task_id)
    if record is None:
        return {"error": "Task not found"}
    return {
        "task_id": record.task_id,
        "task_name": record.task_name,
        "status": record.status.value,
        "submitted_at": record.submitted_at.isoformat(),
        "result": record.result.data if record.result else None,
        "error": record.result.error if record.result else None,
    }


@router.get("", dependencies=[Depends(require_api_key)])
def list_tasks(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    return {"tasks": get_executor().list_tasks(limit=limit)}
