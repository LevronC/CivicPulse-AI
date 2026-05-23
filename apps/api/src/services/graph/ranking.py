from __future__ import annotations

"""
Event ranking engine for global intelligence queries.

Combines recency, velocity, entity centrality, source diversity,
impact score, and sentiment into an intelligence score for pulse
ranking and breaking story detection.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from src.contracts.articles import ArticleEnriched
from src.contracts.enums import SentimentLabel
from src.contracts.graph import (
    BreakingStoryItem,
    EventGraphNode,
    GlobalPulseItem,
)
from src.contracts.events import EventRecord


@dataclass(frozen=True)
class RankingWeights:
    recency: float = 25.0
    velocity: float = 30.0
    impact: float = 20.0
    diversity: float = 10.0
    sentiment: float = 10.0
    entity_centrality: float = 15.0


class EventRankingEngine:
    def __init__(self, weights: RankingWeights | None = None) -> None:
        self._w = weights or RankingWeights()

    def score_event(
        self,
        event: EventRecord,
        *,
        source_diversity: int = 1,
        entity_centrality: float = 0.0,
        now: datetime | None = None,
    ) -> float:
        now = now or datetime.now(timezone.utc)
        recency = self._recency_score(event.last_article_at or event.updated_at, now)
        velocity = self._velocity_score(event.velocity)
        impact = event.impact_score / 100.0
        diversity = min(source_diversity, 5) / 5.0
        sentiment = 1.0 if event.sentiment == SentimentLabel.NEGATIVE else 0.3
        centrality = min(max(entity_centrality, 0.0), 1.0)

        raw = (
            recency * self._w.recency
            + velocity * self._w.velocity
            + impact * self._w.impact
            + diversity * self._w.diversity
            + sentiment * self._w.sentiment
            + centrality * self._w.entity_centrality
        )
        return round(min(raw, 100.0), 2)

    def rank_events(
        self,
        events: list[EventRecord],
        source_counts: dict[str, int],
        entity_centralities: dict[str, float],
        *,
        now: datetime | None = None,
        limit: int = 20,
    ) -> list[GlobalPulseItem]:
        now = now or datetime.now(timezone.utc)
        scored: list[tuple[float, EventRecord]] = []
        for event in events:
            score = self.score_event(
                event,
                source_diversity=source_counts.get(event.id, 1),
                entity_centrality=entity_centralities.get(event.id, 0.0),
                now=now,
            )
            scored.append((score, event))

        scored.sort(key=lambda x: x[0], reverse=True)
        items: list[GlobalPulseItem] = []
        for rank, (score, event) in enumerate(scored[:limit], start=1):
            recency_hours = self._hours_since(event.last_article_at or event.updated_at, now)
            velocity_score = self._velocity_score(event.velocity)
            node = EventGraphNode(
                id=event.id,
                title=event.title,
                summary=event.summary,
                topic=event.topic,
                sentiment=event.sentiment,
                lifecycle=event.lifecycle,
                impact_score=event.impact_score,
                confidence=event.confidence,
                velocity=event.velocity,
                article_count=event.article_count or len(event.article_ids),
                entity_set=event.entity_set,
                article_ids=event.article_ids,
                parent_event_id=event.parent_event_id,
                first_seen_at=event.first_seen_at,
                last_article_at=event.last_article_at,
                updated_at=event.updated_at,
                intelligence_score=score,
            )
            items.append(
                GlobalPulseItem(
                    event=node,
                    rank=rank,
                    velocity=event.velocity,
                    recency_hours=round(recency_hours, 2),
                    source_diversity=source_counts.get(event.id, 1),
                    entity_centrality=entity_centralities.get(event.id, 0.0),
                    velocity_score=round(velocity_score * 100, 2),
                )
            )
        return items

    def breaking_stories(
        self,
        events: list[EventRecord],
        entity_centralities: dict[str, float],
        article_growth: dict[str, int],
        *,
        now: datetime | None = None,
        limit: int = 10,
    ) -> list[BreakingStoryItem]:
        now = now or datetime.now(timezone.utc)
        items: list[BreakingStoryItem] = []

        for event in events:
            age_hours = self._hours_since(event.first_seen_at or event.updated_at, now)
            if age_hours > 72:
                continue

            growth = article_growth.get(event.id, 0)
            velocity = event.velocity
            recency = self._recency_score(event.last_article_at or event.updated_at, now)
            centrality = entity_centralities.get(event.id, 0.0)

            breaking_score = round(
                velocity * 35
                + recency * 25
                + min(growth, 5) * 6
                + centrality * 20
                + (10 if event.sentiment == SentimentLabel.NEGATIVE else 0),
                2,
            )

            if breaking_score < 25 and velocity < 0.3 and growth == 0:
                continue

            signal = self._breaking_signal(velocity, growth, age_hours)
            node = EventGraphNode(
                id=event.id,
                title=event.title,
                summary=event.summary,
                topic=event.topic,
                sentiment=event.sentiment,
                lifecycle=event.lifecycle,
                impact_score=event.impact_score,
                confidence=event.confidence,
                velocity=velocity,
                article_count=event.article_count or len(event.article_ids),
                entity_set=event.entity_set,
                article_ids=event.article_ids,
                parent_event_id=event.parent_event_id,
                first_seen_at=event.first_seen_at,
                last_article_at=event.last_article_at,
                updated_at=event.updated_at,
                intelligence_score=breaking_score,
            )
            items.append(
                BreakingStoryItem(
                    event=node,
                    breaking_score=breaking_score,
                    velocity=velocity,
                    article_growth=growth,
                    hours_active=round(age_hours, 2),
                    signal=signal,
                )
            )

        items.sort(key=lambda x: x.breaking_score, reverse=True)
        return items[:limit]

    def compute_velocity(
        self,
        previous_count: int,
        new_count: int,
        hours_elapsed: float,
    ) -> float:
        if hours_elapsed <= 0:
            return float(new_count - previous_count)
        delta = new_count - previous_count
        return round(max(delta / hours_elapsed, 0.0), 4)

    def novelty_score(self, event: EventRecord, cluster_similarity: float) -> float:
        now = datetime.now(timezone.utc)
        age_hours = self._hours_since(event.first_seen_at or event.updated_at, now)
        recency_boost = max(0.0, 1.0 - age_hours / 24.0)
        dissimilarity = 1.0 - cluster_similarity
        return round((recency_boost * 0.6 + dissimilarity * 0.4) * 100, 2)

    @staticmethod
    def source_diversity(articles: list[ArticleEnriched]) -> int:
        return len({a.source for a in articles})

    @staticmethod
    def _velocity_score(velocity: float) -> float:
        """Non-linear velocity boost — fast-growing stories rank higher."""
        capped = min(max(velocity, 0.0), 5.0)
        return min(capped / 5.0, 1.0) ** 0.7

    @staticmethod
    def _breaking_signal(velocity: float, growth: int, age_hours: float) -> str:
        if velocity >= 2.0 and age_hours <= 12:
            return "accelerating"
        if growth >= 3 and age_hours <= 24:
            return "rapid_growth"
        if age_hours <= 6:
            return "new_story"
        if velocity >= 0.5:
            return "developing"
        return "emerging"

    def _recency_score(self, timestamp: datetime, now: datetime) -> float:
        hours = self._hours_since(timestamp, now)
        if hours <= 1:
            return 1.0
        if hours <= 6:
            return 0.8
        if hours <= 24:
            return 0.5
        if hours <= 72:
            return 0.2
        return 0.05

    @staticmethod
    def _hours_since(timestamp: datetime, now: datetime) -> float:
        return max((now - timestamp).total_seconds() / 3600.0, 0.0)
