"""
Event contracts: DTOs for clustering output, API responses, and storage.

EventRecord  -> persisted event with full metadata
EventSummary -> lightweight projection for list/feed endpoints
EventDetail  -> full event with linked articles for detail views
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.contracts.enums import EventLifecycle, SentimentLabel, Topic


class EventRecord(BaseModel):
    """Canonical event produced by the clustering + scoring pipeline."""

    id: str
    title: str
    summary: str
    topic: Topic
    sentiment: SentimentLabel
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    impact_score: float = Field(ge=0, le=100)
    article_ids: List[str]
    lifecycle: EventLifecycle = EventLifecycle.ACTIVE
    confidence: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Clustering confidence score (0..1)",
    )
    updated_at: datetime
    centroid_embedding: List[float] = Field(default_factory=list)
    entity_set: List[str] = Field(default_factory=list)
    velocity: float = Field(default=0.0, ge=0)
    article_count: int = Field(default=0, ge=0)
    first_seen_at: Optional[datetime] = None
    last_article_at: Optional[datetime] = None
    parent_event_id: Optional[str] = None


class EventSummary(BaseModel):
    """Lightweight event projection for feed/list endpoints."""

    id: str
    title: str
    summary: str
    topic: Topic
    sentiment: SentimentLabel
    latitude: float
    longitude: float
    impact_score: float
    article_count: int
    lifecycle: EventLifecycle
    updated_at: datetime


class EventDetail(BaseModel):
    """Full event with linked enriched articles for detail views."""

    event: EventRecord
    articles: List[dict]
