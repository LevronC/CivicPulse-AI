"""
Graph contracts: entities, edges, mutations, and intelligence query DTOs.

These types describe the living event graph — nodes (events, articles,
entities), edges (belongs_to, related_to, merged_from), and the
mutation results produced by the lifecycle engine.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from src.contracts.enums import EventLifecycle, SentimentLabel, Topic


class RelationshipType(str, Enum):
    BELONGS_TO = "belongs_to"
    RELATED_TO = "related_to"
    MERGED_FROM = "merged_from"
    SPLIT_FROM = "split_from"


class MutationType(str, Enum):
    CREATED = "created"
    ATTACHED = "attached"
    MERGED = "merged"
    SPLIT = "split"
    DECAYED = "decayed"


class EntityRecord(BaseModel):
    id: str
    name: str
    normalized_name: str
    entity_type: str = "unknown"
    created_at: datetime


class GraphEdge(BaseModel):
    id: str
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    weight: float = 0.0
    created_at: datetime


class EventGraphNode(BaseModel):
    """Event node with graph-specific state for intelligence queries."""

    id: str
    title: str
    summary: str
    topic: Topic
    sentiment: SentimentLabel
    lifecycle: EventLifecycle
    impact_score: float
    confidence: float
    velocity: float = 0.0
    article_count: int = 0
    entity_set: List[str] = Field(default_factory=list)
    article_ids: List[str] = Field(default_factory=list)
    parent_event_id: Optional[str] = None
    first_seen_at: Optional[datetime] = None
    last_article_at: Optional[datetime] = None
    updated_at: datetime
    intelligence_score: float = 0.0


class EventSnapshot(BaseModel):
    id: str
    event_id: str
    article_count: int
    sentiment: SentimentLabel
    impact_score: float
    velocity: float
    entity_set: List[str] = Field(default_factory=list)
    snapshot_at: datetime


class GraphMutation(BaseModel):
    mutation_type: MutationType
    event_id: str
    article_id: Optional[str] = None
    related_event_ids: List[str] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)


class ProcessResult(BaseModel):
    articles_processed: int = 0
    mutations: List[GraphMutation] = Field(default_factory=list)
    events_created: int = 0
    events_updated: int = 0
    events_merged: int = 0
    events_split: int = 0
    events_decayed: int = 0


class GlobalPulseItem(BaseModel):
    event: EventGraphNode
    rank: int
    velocity: float
    recency_hours: float
    source_diversity: int
    entity_centrality: float = 0.0
    velocity_score: float = 0.0


class BreakingStoryItem(BaseModel):
    event: EventGraphNode
    breaking_score: float
    velocity: float
    article_growth: int
    hours_active: float
    signal: str


class NarrativeMapNode(BaseModel):
    id: str
    title: str
    topic: Topic
    velocity: float
    article_count: int
    entity_centrality: float
    intelligence_score: float


class NarrativeMapEdge(BaseModel):
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    weight: float
    label: str = ""


class NarrativeMapResponse(BaseModel):
    nodes: List[NarrativeMapNode]
    edges: List[NarrativeMapEdge]
    generated_at: datetime


class TopEntityItem(BaseModel):
    entity: EntityRecord
    event_count: int
    total_articles: int


class StrengthenEdgesResult(BaseModel):
    edges_created: int
    edges_updated: int
    pairs_evaluated: int


class GlobalPulseResponse(BaseModel):
    items: List[GlobalPulseItem]
    generated_at: datetime
    window_hours: float


class EventEvolutionResponse(BaseModel):
    event_id: str
    snapshots: List[EventSnapshot]
    related_events: List[EventGraphNode]
    entities: List[EntityRecord]


class EmergingEventItem(BaseModel):
    event: EventGraphNode
    novelty_score: float
    growth_rate: float


class EntityIntelligenceResponse(BaseModel):
    entity: EntityRecord
    events: List[EventGraphNode]
    total_articles: int
