"""
Domain enumerations shared across all subsystems.

These enums are the canonical source of truth for topic categories,
sentiment labels, and event lifecycle states. Every service, repository,
and API response references these rather than defining local string literals.
"""

from enum import Enum


class Topic(str, Enum):
    POLITICS = "politics"
    DISASTER = "disaster"
    TECHNOLOGY = "technology"
    ECONOMICS = "economics"
    CONFLICT = "conflict"
    OTHER = "other"


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class EventLifecycle(str, Enum):
    """
    Events progress through a lifecycle that determines
    visibility and reprocessing eligibility.

    draft    -> newly clustered, not yet scored
    active   -> scored and visible in feeds
    stale    -> no new articles within decay window
    archived -> manually or automatically retired
    merged   -> absorbed into another event (graph lineage)
    """

    DRAFT = "draft"
    ACTIVE = "active"
    STALE = "stale"
    ARCHIVED = "archived"
    MERGED = "merged"
