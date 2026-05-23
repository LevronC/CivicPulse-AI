"""Unit tests for event projection reconciler."""

from unittest.mock import MagicMock

from src.contracts.enums import EventLifecycle, SentimentLabel, Topic
from src.contracts.events import EventRecord
from src.services.graph.projector import EventProjector
from datetime import datetime, timezone


def _event(event_id: str, article_ids: list[str]) -> EventRecord:
    now = datetime.now(timezone.utc)
    return EventRecord(
        id=event_id,
        title="Test",
        summary="Summary",
        topic=Topic.OTHER,
        sentiment=SentimentLabel.NEUTRAL,
        latitude=0.0,
        longitude=0.0,
        impact_score=10.0,
        article_ids=article_ids,
        lifecycle=EventLifecycle.ACTIVE,
        confidence=0.5,
        updated_at=now,
        article_count=len(article_ids),
    )


class TestEventProjector:
    def test_removes_orphans_and_syncs_article_ids(self):
        graph_repo = MagicMock()
        event_repo = MagicMock()

        graph_repo.get_linked_event_ids.return_value = ["evt-1"]
        graph_repo.delete_orphan_events.return_value = 42
        graph_repo.get_article_ids_for_event.return_value = ["a1", "a2"]
        event_repo.get_event.return_value = _event("evt-1", ["a1"])

        projector = EventProjector(event_repo, graph_repo)
        result = projector.reconcile()

        assert result.orphans_removed == 42
        assert result.events_synced == 1
        assert result.graph_event_count == 1
        event_repo.upsert_event.assert_called_once()

    def test_no_sync_when_article_ids_match(self):
        graph_repo = MagicMock()
        event_repo = MagicMock()

        graph_repo.get_linked_event_ids.return_value = ["evt-1"]
        graph_repo.delete_orphan_events.return_value = 0
        graph_repo.get_article_ids_for_event.return_value = ["a1"]
        event_repo.get_event.return_value = _event("evt-1", ["a1"])

        result = EventProjector(event_repo, graph_repo).reconcile()

        assert result.events_synced == 0
        event_repo.upsert_event.assert_not_called()
