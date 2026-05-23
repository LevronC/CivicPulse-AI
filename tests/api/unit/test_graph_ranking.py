"""Unit tests for event ranking engine."""

from datetime import datetime, timezone, timedelta

from src.contracts.enums import EventLifecycle, SentimentLabel, Topic
from src.contracts.events import EventRecord
from src.services.graph.ranking import EventRankingEngine


def _event(**kwargs) -> EventRecord:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id="evt-test",
        title="Test Event",
        summary="Summary",
        topic=Topic.CONFLICT,
        sentiment=SentimentLabel.NEGATIVE,
        latitude=0.0,
        longitude=0.0,
        impact_score=50.0,
        article_ids=["a1"],
        lifecycle=EventLifecycle.ACTIVE,
        confidence=0.5,
        updated_at=now,
        velocity=2.0,
        article_count=3,
        first_seen_at=now - timedelta(hours=2),
        last_article_at=now - timedelta(minutes=30),
    )
    defaults.update(kwargs)
    return EventRecord(**defaults)


class TestEventRankingEngine:
    def test_recent_high_velocity_event_scores_higher(self):
        ranker = EventRankingEngine()
        recent = _event(velocity=5.0, last_article_at=datetime.now(timezone.utc))
        old = _event(
            id="evt-old",
            velocity=0.1,
            last_article_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        assert ranker.score_event(recent) > ranker.score_event(old)

    def test_rank_events_orders_by_score(self):
        ranker = EventRankingEngine()
        e1 = _event(id="evt-1", velocity=1.0, impact_score=30.0)
        e2 = _event(id="evt-2", velocity=8.0, impact_score=80.0)
        items = ranker.rank_events([e1, e2], {"evt-1": 1, "evt-2": 3}, {"evt-1": 0.2, "evt-2": 0.8})
        assert items[0].event.id == "evt-2"

    def test_compute_velocity(self):
        ranker = EventRankingEngine()
        assert ranker.compute_velocity(2, 5, 1.0) == 3.0
        assert ranker.compute_velocity(5, 5, 2.0) == 0.0

    def test_entity_centrality_boosts_score(self):
        ranker = EventRankingEngine()
        base = _event(id="evt-base", velocity=1.0)
        central = _event(id="evt-central", velocity=1.0)
        low = ranker.score_event(base, entity_centrality=0.1)
        high = ranker.score_event(central, entity_centrality=0.9)
        assert high > low

    def test_breaking_stories_ranks_by_velocity(self):
        ranker = EventRankingEngine()
        fast = _event(id="evt-fast", velocity=3.0)
        slow = _event(id="evt-slow", velocity=0.1)
        items = ranker.breaking_stories(
            [slow, fast],
            {"evt-fast": 0.5, "evt-slow": 0.1},
            {"evt-fast": 4, "evt-slow": 0},
            limit=5,
        )
        assert items[0].event.id == "evt-fast"
        assert items[0].signal in ("accelerating", "rapid_growth", "new_story", "developing", "emerging")
