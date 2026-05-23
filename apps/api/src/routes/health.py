"""Health check and diagnostics endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.repositories.database import DatabaseSession
from src.services.enrichment.models.manager import get_model_manager

router = APIRouter(tags=["health"])


@router.get("/health")
def health(session: Session = Depends(DatabaseSession)) -> dict:
    try:
        session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "degraded"

    return {"status": "ok", "database": db_status}


@router.get("/health/models")
def model_status() -> dict:
    """Report which models are registered and their loading state."""
    return {"models": get_model_manager().status()}
