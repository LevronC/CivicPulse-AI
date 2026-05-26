from __future__ import annotations

import os
import re

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://civicpulse:civicpulse@localhost:5432/civicpulse"
)

_DATABASE_URL_KEYS = (
    "DATABASE_URL",
    "POSTGRES_URL",
    "DATABASE_URL_UNPOOLED",
    "POSTGRES_URL_NON_POOLING",
)


def _clean_env_value(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().strip('"').strip("'")


def normalize_database_url(url: str) -> str:
    """Convert Neon/Vercel URLs to SQLAlchemy psycopg3 format."""
    cleaned = _clean_env_value(url)
    if not cleaned:
        return DEFAULT_DATABASE_URL

    if cleaned.startswith("postgres://"):
        cleaned = "postgresql+psycopg://" + cleaned[len("postgres://") :]
    elif cleaned.startswith("postgresql://"):
        cleaned = "postgresql+psycopg://" + cleaned[len("postgresql://") :]

    return cleaned


def resolve_database_url() -> str:
    """
    Pick the first non-empty database URL from common Neon/Vercel env vars.

    Empty DATABASE_URL="" (often set by storage integrations) must not override
    a valid POSTGRES_URL.
    """
    for key in _DATABASE_URL_KEYS:
        candidate = _clean_env_value(os.getenv(key))
        if candidate:
            return normalize_database_url(candidate)
    return DEFAULT_DATABASE_URL


def is_vercel_runtime() -> bool:
    return bool(os.getenv("VERCEL"))
