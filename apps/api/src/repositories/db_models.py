"""
SQLAlchemy ORM models mapping to the PostgreSQL schema.

These models are persistence-layer concerns only — they are never
exposed directly to API consumers. The repository layer converts
between ORM models and domain contracts (Pydantic DTOs).
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ArticleRow(Base):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    language: Mapped[str] = mapped_column(String, nullable=False)
    inserted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class EnrichmentRow(Base):
    __tablename__ = "article_enrichment"

    article_id: Mapped[str] = mapped_column(
        String, ForeignKey("articles.id"), primary_key=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    sentiment: Mapped[str] = mapped_column(String, nullable=False)
    entities: Mapped[dict] = mapped_column(JSONB, nullable=False)
    embedding: Mapped[list] = mapped_column(JSONB, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False, default="heuristic-v1")
    enriched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class EventRow(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    sentiment: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False)
    article_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    lifecycle: Mapped[str] = mapped_column(String, nullable=False, default="active")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    centroid_embedding: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    entity_set: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    velocity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_article_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_event_id: Mapped[str | None] = mapped_column(String, ForeignKey("events.id"), nullable=True)
    article_count: Mapped[int] = mapped_column(nullable=False, default=0)


class EntityRow(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class EventEntityRow(Base):
    __tablename__ = "event_entities"

    event_id: Mapped[str] = mapped_column(String, ForeignKey("events.id"), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String, ForeignKey("entities.id"), primary_key=True)
    mention_count: Mapped[int] = mapped_column(nullable=False, default=1)


class EventRelationshipRow(Base):
    __tablename__ = "event_relationships"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_event_id: Mapped[str] = mapped_column(String, ForeignKey("events.id"), nullable=False)
    target_event_id: Mapped[str] = mapped_column(String, ForeignKey("events.id"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ArticleEventLinkRow(Base):
    __tablename__ = "article_event_links"

    article_id: Mapped[str] = mapped_column(String, ForeignKey("articles.id"), primary_key=True)
    event_id: Mapped[str] = mapped_column(String, ForeignKey("events.id"), primary_key=True)
    similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class EventSnapshotRow(Base):
    __tablename__ = "event_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    event_id: Mapped[str] = mapped_column(String, ForeignKey("events.id"), nullable=False)
    article_count: Mapped[int] = mapped_column(nullable=False)
    sentiment: Mapped[str] = mapped_column(String, nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False)
    velocity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    entity_set: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
