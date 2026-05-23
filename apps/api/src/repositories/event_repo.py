from __future__ import annotations

"""
Event repository — persistence boundary for clustered events.

Handles event upsert (rebuild operations replace all events),
filtered queries, and single-event lookups. Filters are pushed
to SQL to avoid loading the full table into memory.
"""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.contracts.enums import EventLifecycle, SentimentLabel, Topic
from src.contracts.events import EventRecord, EventSummary
from src.contracts.pagination import PaginatedResponse, PaginationParams
from src.logging import get_logger
from src.repositories.db_models import ArticleEventLinkRow, EventRow

logger = get_logger("repo.event")


class EventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_event(self, event: EventRecord) -> None:
        """
        Upsert an event during rebuild or incremental graph mutation.
        """
        stmt = (
            pg_insert(EventRow)
            .values(
                id=event.id,
                title=event.title,
                summary=event.summary,
                topic=event.topic.value,
                sentiment=event.sentiment.value,
                latitude=event.latitude,
                longitude=event.longitude,
                impact_score=event.impact_score,
                article_ids=event.article_ids,
                lifecycle=event.lifecycle.value,
                confidence=event.confidence,
                updated_at=event.updated_at,
                centroid_embedding=event.centroid_embedding,
                entity_set=event.entity_set,
                velocity=event.velocity,
                first_seen_at=event.first_seen_at,
                last_article_at=event.last_article_at,
                parent_event_id=event.parent_event_id,
                article_count=event.article_count or len(event.article_ids),
            )
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "title": event.title,
                    "summary": event.summary,
                    "topic": event.topic.value,
                    "sentiment": event.sentiment.value,
                    "latitude": event.latitude,
                    "longitude": event.longitude,
                    "impact_score": event.impact_score,
                    "article_ids": event.article_ids,
                    "lifecycle": event.lifecycle.value,
                    "confidence": event.confidence,
                    "updated_at": event.updated_at,
                    "centroid_embedding": event.centroid_embedding,
                    "entity_set": event.entity_set,
                    "velocity": event.velocity,
                    "first_seen_at": event.first_seen_at,
                    "last_article_at": event.last_article_at,
                    "parent_event_id": event.parent_event_id,
                    "article_count": event.article_count or len(event.article_ids),
                },
            )
        )
        self._session.execute(stmt)

    def clear_all(self) -> int:
        """Delete all events. Used before full rebuild."""
        count = self._session.query(EventRow).delete()
        logger.info("Events cleared for rebuild", extra={"deleted": count})
        return count

    def list_events(
        self,
        pagination: PaginationParams,
        *,
        topic: Topic | None = None,
        sentiment: SentimentLabel | None = None,
        min_impact: float = 0.0,
        lifecycle: EventLifecycle | None = None,
        graph_only: bool = False,
    ) -> PaginatedResponse[EventSummary]:
        query = select(EventRow)

        if graph_only:
            query = query.join(
                ArticleEventLinkRow,
                EventRow.id == ArticleEventLinkRow.event_id,
            ).distinct()

        if topic:
            query = query.where(EventRow.topic == topic.value)
        if sentiment:
            query = query.where(EventRow.sentiment == sentiment.value)
        if min_impact > 0:
            query = query.where(EventRow.impact_score >= min_impact)
        if lifecycle:
            query = query.where(EventRow.lifecycle == lifecycle.value)

        count_query = query.with_only_columns(EventRow.id)
        total = len(self._session.execute(count_query).all())

        query = (
            query
            .order_by(EventRow.impact_score.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        rows = self._session.execute(query).scalars().all()

        items = [
            EventSummary(
                id=r.id,
                title=r.title,
                summary=r.summary,
                topic=Topic(r.topic),
                sentiment=SentimentLabel(r.sentiment),
                latitude=r.latitude,
                longitude=r.longitude,
                impact_score=r.impact_score,
                article_count=len(r.article_ids),
                lifecycle=EventLifecycle(r.lifecycle),
                updated_at=r.updated_at,
            )
            for r in rows
        ]

        next_offset = pagination.offset + pagination.limit
        return PaginatedResponse(
            items=items,
            total=total,
            offset=pagination.offset,
            limit=pagination.limit,
            next_cursor=str(next_offset) if next_offset < total else None,
        )

    def get_event(self, event_id: str) -> EventRecord | None:
        row = self._session.get(EventRow, event_id)
        if row is None:
            return None
        return self._row_to_record(row)

    def list_active_by_topic(self, topic: Topic) -> list[EventRecord]:
        stmt = select(EventRow).where(
            EventRow.topic == topic.value,
            EventRow.lifecycle.in_(["active", "stale"]),
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._row_to_record(r) for r in rows]

    def list_all_active(self, *, graph_only: bool = False) -> list[EventRecord]:
        query = select(EventRow).where(
            EventRow.lifecycle.in_(["active", "stale"])
        )
        if graph_only:
            query = query.join(
                ArticleEventLinkRow,
                EventRow.id == ArticleEventLinkRow.event_id,
            ).distinct()
        query = query.order_by(EventRow.velocity.desc())
        rows = self._session.execute(query).scalars().all()
        return [self._row_to_record(r) for r in rows]

    @staticmethod
    def _row_to_record(row: EventRow) -> EventRecord:
        return EventRecord(
            id=row.id,
            title=row.title,
            summary=row.summary,
            topic=Topic(row.topic),
            sentiment=SentimentLabel(row.sentiment),
            latitude=row.latitude,
            longitude=row.longitude,
            impact_score=row.impact_score,
            article_ids=row.article_ids or [],
            lifecycle=EventLifecycle(row.lifecycle),
            confidence=row.confidence,
            updated_at=row.updated_at,
            centroid_embedding=row.centroid_embedding or [],
            entity_set=row.entity_set or [],
            velocity=row.velocity or 0.0,
            article_count=row.article_count or len(row.article_ids or []),
            first_seen_at=row.first_seen_at,
            last_article_at=row.last_article_at,
            parent_event_id=row.parent_event_id,
        )

    def count(self) -> int:
        return self._session.query(EventRow).count()
