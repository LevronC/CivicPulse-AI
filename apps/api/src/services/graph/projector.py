from __future__ import annotations

"""
Event projection layer — materializes graph truth into the events table.

The event graph (article_event_links + lifecycle mutations) is the
canonical source of truth. The events table is a read-optimized
projection for legacy API compatibility.

This module removes orphan rows written by the deprecated batch
rebuild path and syncs article_ids/article_count from graph links.
"""

from dataclasses import dataclass

from src.logging import get_logger
from src.repositories.event_repo import EventRepository
from src.repositories.graph_repo import GraphRepository

logger = get_logger("graph.projector")


@dataclass(frozen=True)
class ProjectionResult:
    orphans_removed: int
    events_synced: int
    graph_event_count: int


class EventProjector:
    def __init__(
        self,
        event_repo: EventRepository,
        graph_repo: GraphRepository,
    ) -> None:
        self._events = event_repo
        self._graph = graph_repo

    def reconcile(self) -> ProjectionResult:
        """
        Align the events SQL projection with graph link truth.

        1. Delete events with no article→event graph links (batch orphans)
        2. Sync article_ids and article_count from links for remaining events
        """
        linked_event_ids = self._graph.get_linked_event_ids()
        orphans_removed = self._graph.delete_orphan_events()
        events_synced = 0

        for event_id in linked_event_ids:
            event = self._events.get_event(event_id)
            if event is None:
                continue
            linked_article_ids = self._graph.get_article_ids_for_event(event_id)
            if linked_article_ids != event.article_ids:
                event.article_ids = linked_article_ids
                event.article_count = len(linked_article_ids)
                self._events.upsert_event(event)
                events_synced += 1

        result = ProjectionResult(
            orphans_removed=orphans_removed,
            events_synced=events_synced,
            graph_event_count=len(linked_event_ids),
        )
        logger.info("Event projection reconciled", extra={"result": result.__dict__})
        return result
