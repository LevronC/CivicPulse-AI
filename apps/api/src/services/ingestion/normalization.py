from __future__ import annotations

"""
Provider payload normalization helpers.

Purpose:
  Keep source-specific adapters small while centralizing validation, datetime
  parsing, HTML cleanup, and ArticleCreate construction.

Responsibilities:
  Convert imperfect external payloads into strict internal contracts and drop
  records that cannot meet minimum ingestion requirements.

Extension points:
  Add provider-specific date or body extraction helpers here only when the
  behavior is reusable across more than one adapter.

Future replacement strategy:
  A richer normalization service can replace these helpers later while still
  returning ArticleCreate contracts to SourceAdapter implementations.
"""

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from src.contracts.articles import ArticleCreate
from src.services.ingestion.types import SourceNormalizationError

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def clean_text(value: object | None) -> str:
    """Normalize provider text fields into compact plain text."""

    if value is None:
        return ""
    text = html.unescape(str(value))
    text = _TAG_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def parse_provider_datetime(value: object | None) -> datetime:
    """Parse common provider date formats into timezone-aware UTC datetimes."""

    if not value:
        raise SourceNormalizationError("published_at is required")

    raw = str(value).strip()
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            parsed = None

    if parsed is None:
        raise SourceNormalizationError(f"Could not parse datetime: {raw}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_gdelt_datetime(value: object | None) -> datetime:
    """Parse GDELT seendate values such as 20240522T153000Z."""

    if not value:
        raise SourceNormalizationError("GDELT seendate is required")
    raw = str(value).strip()
    try:
        return datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise SourceNormalizationError(f"Could not parse GDELT datetime: {raw}") from exc


def build_article(
    *,
    source: str,
    url: object | None,
    title: object | None,
    body: object | None,
    published_at: datetime,
    language: object | None = "en",
) -> ArticleCreate:
    """Build a validated ArticleCreate from normalized provider fields."""

    normalized_url = clean_text(url)
    normalized_title = clean_text(title)
    normalized_body = clean_text(body)
    normalized_language = clean_text(language or "en")[:5] or "en"

    if not normalized_url:
        raise SourceNormalizationError("url is required")
    if not normalized_title:
        raise SourceNormalizationError("title is required")
    if not normalized_body:
        normalized_body = normalized_title

    return ArticleCreate(
        source=source,
        url=normalized_url,
        title=normalized_title,
        body=normalized_body,
        published_at=published_at,
        language=normalized_language,
    )
