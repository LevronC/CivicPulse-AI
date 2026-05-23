from __future__ import annotations

"""
Database session management and engine initialization.

Uses SQLAlchemy async-compatible session factory with connection pooling.
The session dependency (DatabaseSession) is injected into route handlers
via FastAPI's Depends() — repositories never create their own sessions.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings
from src.logging import get_logger

logger = get_logger("database")

_session_factory: sessionmaker[Session] | None = None


def init_db() -> sessionmaker[Session]:
    """
    Initialize the database engine and session factory.

    Called once at application startup. Connection pool settings
    come from typed configuration to ensure they match deployment
    constraints (e.g., managed Postgres connection limits).
    """
    global _session_factory

    settings = get_settings()
    engine = create_engine(
        settings.db.url,
        pool_size=settings.db.pool_size,
        max_overflow=settings.db.pool_overflow,
        pool_pre_ping=True,
        echo=settings.environment == "development",
    )
    _session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    logger.info("Database engine initialized", extra={"pool_size": settings.db.pool_size})
    return _session_factory


def get_session_factory() -> sessionmaker[Session]:
    if _session_factory is None:
        return init_db()
    return _session_factory


def DatabaseSession() -> Session:
    """
    FastAPI dependency that yields a database session.
    Commits on success, rolls back on exception.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session  # type: ignore[misc]
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
