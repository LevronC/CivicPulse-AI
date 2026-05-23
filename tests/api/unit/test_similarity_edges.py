"""Unit tests for similarity edge strengthener."""

from unittest.mock import MagicMock

from src.contracts.enums import EventLifecycle, SentimentLabel, Topic
from src.contracts.events import EventRecord
from src.services.graph.similarity_edges import SimilarityEdgeService
from datetime import datetime, timezone


def _event(event_id: str, embedding: list[float], entities: list[str]) -> EventRecord:
    now = datetime.now(timezone.utc)
    return EventRecord(
        id=event_id,
        title="Test",
        summary="Summary",
        topic=Topic.DISASTER,
        sentiment=SentimentLabel.NEUTRAL,
        latitude=0.0,
        longitude=0.0,
        impact_score=10.0,
        article_ids=["a1"],
        lifecycle=EventLifecycle.ACTIVE,
        confidence=0.5,
        updated_at=now,
        centroid_embedding=embedding,
        entity_set=entities,
        article_count=1,
    )


class TestSimilarityEdgeService:
    def test_creates_edge_for_similar_events(self):
        graph_repo = MagicMock()
        graph_repo.upsert_relationship.return_value = True
        service = SimilarityEdgeService(graph_repo)

        e1 = _event("e1", [1.0, 0.0], ["congo", "ebola"])
        e2 = _event("e2", [0.99, 0.01], ["congo", "outbreak"])

        stats = service.strengthen([e1, e2])

        assert stats["pairs_evaluated"] == 1
        assert stats["edges_created"] == 1
        graph_repo.upsert_relationship.assert_called_once()

    def test_skips_dissimilar_events(self):
        graph_repo = MagicMock()
        service = SimilarityEdgeService(graph_repo)

        e1 = _event("e1", [1.0, 0.0], ["alpha"])
        e2 = _event("e2", [0.0, 1.0], ["beta"])

        stats = service.strengthen([e1, e2])

        assert stats["edges_created"] == 0
        graph_repo.upsert_relationship.assert_not_called()
