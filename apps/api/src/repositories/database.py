from __future__ import annotations

"""
Database session management and engine initialization.

Uses SQLAlchemy async-compatible session factory with connection pooling.
The session dependency (DatabaseSession) is injected into route handlers
via FastAPI's Depends() — repositories never create their own sessions.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from src.config import get_settings
from src.config.database_url import is_vercel_runtime
from src.logging import get_logger

logger = get_logger("database")

_session_factory: sessionmaker[Session] | None = None
_schema_ready = False


def _ensure_schema(engine) -> None:
    global _schema_ready
    if _schema_ready:
        return
    from src.repositories.db_models import Base

    Base.metadata.create_all(engine)
    _schema_ready = True
    logger.info("Database schema ensured")


def init_db() -> sessionmaker[Session]:
    """
    Initialize the database engine and session factory.

    Called once at application startup. Connection pool settings
    come from typed configuration to ensure they match deployment
    constraints (e.g., managed Postgres connection limits).
    """
    global _session_factory

    settings = get_settings()
    engine_kwargs: dict = {
        "pool_pre_ping": True,
        "echo": settings.environment == "development",
    }

    if is_vercel_runtime() or os.getenv("DB_USE_NULL_POOL", "").lower() == "true":
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = settings.db.pool_size
        engine_kwargs["max_overflow"] = settings.db.pool_overflow

    engine = create_engine(settings.db.url, **engine_kwargs)

    if is_vercel_runtime() or os.getenv("AUTO_INIT_SCHEMA", "").lower() == "true":
        try:
            _ensure_schema(engine)
        except Exception as exc:
            logger.warning("Schema init skipped: %s", exc)

    _session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    logger.info(
        "Database engine initialized",
        extra={
            "pool": "null" if "poolclass" in engine_kwargs else "queued",
        },
    )
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
