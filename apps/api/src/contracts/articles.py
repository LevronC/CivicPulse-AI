"""
Article contracts: DTOs for ingestion, enrichment, and storage boundaries.

ArticleCreate    -> inbound payload from source connectors
ArticleRecord    -> persisted article (with generated id + timestamps)
StageMetadata    -> provenance from a single enrichment stage
EnrichmentResult -> composite output from the full NLP pipeline
ArticleEnriched  -> fully enriched article ready for clustering
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from src.contracts.enums import SentimentLabel, Topic


class ArticleCreate(BaseModel):
    """Inbound article from a source connector."""

    source: str = Field(min_length=1, max_length=64)
    url: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=512)
    body: str = Field(min_length=1)
    published_at: datetime
    language: str = Field(default="en", min_length=2, max_length=5)

    @model_validator(mode="after")
    def validate_fields(self) -> "ArticleCreate":
        if self.published_at.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")
        return self


class ArticleRecord(BaseModel):
    """Persisted article with server-generated fields."""

    id: str
    source: str
    url: str
    title: str
    body: str
    published_at: datetime
    language: str
    inserted_at: datetime


class StageMetadata(BaseModel):
    """
    Provenance record for a single enrichment stage execution.

    Captures which model produced the output, its confidence level,
    processing time, and any warnings encountered during execution.
    """

    model_config = {"protected_namespaces": ()}

    stage_name: str
    model_name: str = "heuristic"
    model_version: str = "v1"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    latency_ms: float = 0.0
    timestamp: Optional[datetime] = None
    warnings: List[str] = Field(default_factory=list)


class EnrichmentResult(BaseModel):
    """
    Composite output of the NLP enrichment pipeline for a single article.

    Each field may be None if the corresponding enrichment stage
    failed — downstream consumers must handle partial enrichment
    gracefully rather than discarding the entire record.

    stage_metadata captures per-stage provenance so operators can
    trace which model version produced each output and identify
    stages with degraded confidence.
    """

    summary: Optional[str] = None
    topic: Optional[Topic] = None
    sentiment: Optional[SentimentLabel] = None
    entities: List[str] = Field(default_factory=list)
    embedding: List[float] = Field(default_factory=list)

    enrichment_version: str = Field(
        default="heuristic-v1",
        description="Provenance tag for the pipeline version",
    )
    total_latency_ms: float = 0.0
    stage_metadata: List[StageMetadata] = Field(default_factory=list)
    processed_at: Optional[datetime] = None
    stages_succeeded: int = 0
    stages_failed: int = 0

    @property
    def is_partial(self) -> bool:
        return self.stages_failed > 0 and self.stages_succeeded > 0

    @property
    def avg_confidence(self) -> float:
        if not self.stage_metadata:
            return 0.0
        return sum(s.confidence for s in self.stage_metadata) / len(self.stage_metadata)


class ArticleEnriched(ArticleRecord):
    """Article record joined with enrichment outputs."""

    summary: str
    topic: Topic
    sentiment: SentimentLabel
    entities: List[str]
    embedding: List[float]
    enriched_at: datetime
