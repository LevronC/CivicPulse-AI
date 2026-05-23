from __future__ import annotations

"""
Graph repository — persistence for entities, edges, links, and snapshots.

This is the storage boundary for the event graph. The lifecycle engine
never constructs SQL directly; it calls repository methods that return
domain contracts.
"""

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.contracts.enums import SentimentLabel
from src.contracts.graph import (
    EntityRecord,
    EventSnapshot,
    GraphEdge,
    RelationshipType,
)
from src.logging import get_logger
from src.repositories.db_models import (
    ArticleEventLinkRow,
    EntityRow,
    EventEntityRow,
    EventRelationshipRow,
    EventSnapshotRow,
)

logger = get_logger("repo.graph")


class GraphRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_entity(self, name: str, entity_type: str = "unknown") -> EntityRecord:
        normalized = name.strip().lower()
        entity_id = "ent-" + hashlib.sha256(normalized.encode()).hexdigest()[:12]

        stmt = (
            pg_insert(EntityRow)
            .values(
                id=entity_id,
                name=name.strip(),
                normalized_name=normalized,
                entity_type=entity_type,
            )
            .on_conflict_do_nothing(index_elements=["normalized_name"])
        )
        self._session.execute(stmt)
        row = self._session.get(EntityRow, entity_id)
        if row is None:
            row = self._session.execute(
                select(EntityRow).where(EntityRow.normalized_name == normalized)
            ).scalar_one()

        return EntityRecord(
            id=row.id,
            name=row.name,
            normalized_name=row.normalized_name,
            entity_type=row.entity_type,
            created_at=row.created_at,
        )

    def link_event_entity(self, event_id: str, entity_id: str, mention_count: int = 1) -> None:
        stmt = (
            pg_insert(EventEntityRow)
            .values(event_id=event_id, entity_id=entity_id, mention_count=mention_count)
            .on_conflict_do_update(
                index_elements=["event_id", "entity_id"],
                set_={"mention_count": EventEntityRow.mention_count + mention_count},
            )
        )
        self._session.execute(stmt)

    def link_article_event(
        self, article_id: str, event_id: str, similarity: float
    ) -> None:
        stmt = (
            pg_insert(ArticleEventLinkRow)
            .values(
                article_id=article_id,
                event_id=event_id,
                similarity=similarity,
                linked_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_update(
                index_elements=["article_id", "event_id"],
                set_={"similarity": similarity},
            )
        )
        self._session.execute(stmt)

    def is_article_linked(self, article_id: str) -> bool:
        stmt = select(ArticleEventLinkRow.article_id).where(
            ArticleEventLinkRow.article_id == article_id
        )
        return self._session.execute(stmt).scalar_one_or_none() is not None

    def get_unlinked_article_ids(self, limit: int = 50) -> list[str]:
        from src.repositories.db_models import ArticleRow, EnrichmentRow

        stmt = (
            select(ArticleRow.id)
            .join(EnrichmentRow, ArticleRow.id == EnrichmentRow.article_id)
            .outerjoin(
                ArticleEventLinkRow,
                ArticleRow.id == ArticleEventLinkRow.article_id,
            )
            .where(ArticleEventLinkRow.article_id.is_(None))
            .order_by(ArticleRow.published_at.asc())
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())

    def add_relationship(
        self,
        source_event_id: str,
        target_event_id: str,
        relationship_type: RelationshipType,
        weight: float = 0.0,
    ) -> GraphEdge:
        edge_id = f"rel-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        row = EventRelationshipRow(
            id=edge_id,
            source_event_id=source_event_id,
            target_event_id=target_event_id,
            relationship_type=relationship_type.value,
            weight=weight,
            created_at=now,
        )
        self._session.add(row)
        return GraphEdge(
            id=edge_id,
            source_id=source_event_id,
            target_id=target_event_id,
            relationship_type=relationship_type,
            weight=weight,
            created_at=now,
        )

    def upsert_relationship(
        self,
        source_event_id: str,
        target_event_id: str,
        relationship_type: RelationshipType,
        weight: float = 0.0,
    ) -> bool:
        """
        Create or update a relationship edge.

        Returns True if a new edge was created, False if an existing
        edge was updated.
        """
        left, right = sorted([source_event_id, target_event_id])
        stmt = select(EventRelationshipRow).where(
            EventRelationshipRow.relationship_type == relationship_type.value,
            or_(
                and_(
                    EventRelationshipRow.source_event_id == left,
                    EventRelationshipRow.target_event_id == right,
                ),
                and_(
                    EventRelationshipRow.source_event_id == right,
                    EventRelationshipRow.target_event_id == left,
                ),
            ),
        )
        existing = self._session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            if weight > existing.weight:
                existing.weight = weight
            return False

        self.add_relationship(left, right, relationship_type, weight)
        return True

    def list_relationships(
        self,
        *,
        relationship_type: RelationshipType | None = None,
        limit: int = 200,
    ) -> list[GraphEdge]:
        stmt = select(EventRelationshipRow)
        if relationship_type is not None:
            stmt = stmt.where(
                EventRelationshipRow.relationship_type == relationship_type.value
            )
        stmt = stmt.order_by(EventRelationshipRow.weight.desc()).limit(limit)
        rows = self._session.execute(stmt).scalars().all()
        return [
            GraphEdge(
                id=r.id,
                source_id=r.source_event_id,
                target_id=r.target_event_id,
                relationship_type=RelationshipType(r.relationship_type),
                weight=r.weight,
                created_at=r.created_at,
            )
            for r in rows
        ]

    def get_entity_counts_for_events(self, event_ids: list[str]) -> dict[str, int]:
        if not event_ids:
            return {}
        stmt = (
            select(EventEntityRow.event_id, func.count(EventEntityRow.entity_id))
            .where(EventEntityRow.event_id.in_(event_ids))
            .group_by(EventEntityRow.event_id)
        )
        rows = self._session.execute(stmt).all()
        return {event_id: int(count) for event_id, count in rows}

    def count_shared_entity_neighbors(self, event_ids: list[str]) -> dict[str, int]:
        """Count other events sharing at least one entity with each event."""
        if not event_ids:
            return {}

        stmt = (
            select(EventEntityRow.event_id, EventEntityRow.entity_id)
            .where(EventEntityRow.event_id.in_(event_ids))
        )
        rows = self._session.execute(stmt).all()
        event_entities: dict[str, set[str]] = {}
        for event_id, entity_id in rows:
            event_entities.setdefault(event_id, set()).add(entity_id)

        entity_to_events: dict[str, set[str]] = {}
        for event_id, entities in event_entities.items():
            for entity_id in entities:
                entity_to_events.setdefault(entity_id, set()).add(event_id)

        neighbors: dict[str, int] = {eid: 0 for eid in event_ids}
        for event_id, entities in event_entities.items():
            related: set[str] = set()
            for entity_id in entities:
                related.update(entity_to_events.get(entity_id, set()))
            related.discard(event_id)
            neighbors[event_id] = len(related)
        return neighbors

    def search_top_entities(self, *, limit: int = 20) -> list[tuple[EntityRecord, int, int]]:
        """Return entities ranked by linked event count."""
        stmt = (
            select(
                EntityRow,
                func.count(func.distinct(EventEntityRow.event_id)).label("event_count"),
                func.sum(EventEntityRow.mention_count).label("mentions"),
            )
            .join(EventEntityRow, EntityRow.id == EventEntityRow.entity_id)
            .group_by(EntityRow.id)
            .order_by(func.count(func.distinct(EventEntityRow.event_id)).desc())
            .limit(limit)
        )
        rows = self._session.execute(stmt).all()
        results: list[tuple[EntityRecord, int, int]] = []
        for row, event_count, mentions in rows:
            results.append((
                EntityRecord(
                    id=row.id,
                    name=row.name,
                    normalized_name=row.normalized_name,
                    entity_type=row.entity_type,
                    created_at=row.created_at,
                ),
                int(event_count),
                int(mentions or 0),
            ))
        return results

    def get_related_events(self, event_id: str) -> list[str]:
        stmt = select(EventRelationshipRow).where(
            (EventRelationshipRow.source_event_id == event_id)
            | (EventRelationshipRow.target_event_id == event_id)
        )
        rows = self._session.execute(stmt).scalars().all()
        related: set[str] = set()
        for row in rows:
            if row.source_event_id != event_id:
                related.add(row.source_event_id)
            if row.target_event_id != event_id:
                related.add(row.target_event_id)
        return list(related)

    def record_snapshot(
        self,
        event_id: str,
        article_count: int,
        sentiment: str,
        impact_score: float,
        velocity: float,
        entity_set: list[str],
    ) -> EventSnapshot:
        snapshot_id = f"snap-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        row = EventSnapshotRow(
            id=snapshot_id,
            event_id=event_id,
            article_count=article_count,
            sentiment=sentiment,
            impact_score=impact_score,
            velocity=velocity,
            entity_set=entity_set,
            snapshot_at=now,
        )
        self._session.add(row)
        return EventSnapshot(
            id=snapshot_id,
            event_id=event_id,
            article_count=article_count,
            sentiment=SentimentLabel(sentiment),
            impact_score=impact_score,
            velocity=velocity,
            entity_set=entity_set,
            snapshot_at=now,
        )

    def get_snapshots(self, event_id: str, limit: int = 50) -> list[EventSnapshot]:
        stmt = (
            select(EventSnapshotRow)
            .where(EventSnapshotRow.event_id == event_id)
            .order_by(EventSnapshotRow.snapshot_at.desc())
            .limit(limit)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [
            EventSnapshot(
                id=r.id,
                event_id=r.event_id,
                article_count=r.article_count,
                sentiment=SentimentLabel(r.sentiment),
                impact_score=r.impact_score,
                velocity=r.velocity,
                entity_set=r.entity_set or [],
                snapshot_at=r.snapshot_at,
            )
            for r in rows
        ]

    def get_entities_for_event(self, event_id: str) -> list[EntityRecord]:
        stmt = (
            select(EntityRow)
            .join(EventEntityRow, EntityRow.id == EventEntityRow.entity_id)
            .where(EventEntityRow.event_id == event_id)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [
            EntityRecord(
                id=r.id,
                name=r.name,
                normalized_name=r.normalized_name,
                entity_type=r.entity_type,
                created_at=r.created_at,
            )
            for r in rows
        ]

    def get_events_for_entity(self, normalized_name: str) -> list[str]:
        stmt = (
            select(EventEntityRow.event_id)
            .join(EntityRow, EntityRow.id == EventEntityRow.entity_id)
            .where(EntityRow.normalized_name == normalized_name.strip().lower())
        )
        return list(self._session.execute(stmt).scalars().all())

    def get_linked_event_ids(self) -> list[str]:
        stmt = select(ArticleEventLinkRow.event_id).distinct()
        return list(self._session.execute(stmt).scalars().all())

    def get_article_ids_for_event(self, event_id: str) -> list[str]:
        stmt = (
            select(ArticleEventLinkRow.article_id)
            .where(ArticleEventLinkRow.event_id == event_id)
            .order_by(ArticleEventLinkRow.linked_at.asc())
        )
        return list(self._session.execute(stmt).scalars().all())

    def delete_orphan_events(self) -> int:
        """Remove events with no article→event graph links (batch rebuild artifacts)."""
        from src.repositories.db_models import EventRow

        linked = select(ArticleEventLinkRow.event_id).distinct()
        stmt = select(EventRow.id).where(EventRow.id.not_in(linked))
        orphan_ids = list(self._session.execute(stmt).scalars().all())
        if not orphan_ids:
            return 0
        deleted = (
            self._session.query(EventRow)
            .filter(EventRow.id.in_(orphan_ids))
            .delete(synchronize_session=False)
        )
        logger.info("Orphan events removed", extra={"deleted": deleted})
        return deleted

    def count_linked_events(self) -> int:
        return len(self.get_linked_event_ids())

    def get_entity_by_name(self, name: str) -> EntityRecord | None:
        normalized = name.strip().lower()
        stmt = select(EntityRow).where(EntityRow.normalized_name == normalized)
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return EntityRecord(
            id=row.id,
            name=row.name,
            normalized_name=row.normalized_name,
            entity_type=row.entity_type,
            created_at=row.created_at,
        )
