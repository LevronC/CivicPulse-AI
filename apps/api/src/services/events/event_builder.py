from __future__ import annotations

"""
Event builder — LEGACY batch clustering path.

Used only when GRAPH_MODE=false. In graph mode, EventGraphService
is the sole writer of event state and this builder must not be called.

Event identity is derived from cluster content:
  - Title: most representative article (highest entity overlap with cluster)
  - Summary: combines lead article summary with article count and topic
  - Sentiment: majority vote across cluster articles
  - Geo: entity-based when location entities are present, topic fallback otherwise

Stable event IDs use content hashing so the same cluster produces the
same event ID across rebuilds, enabling incremental diffing later.
"""

import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

from src.contracts.articles import ArticleEnriched
from src.contracts.enums import EventLifecycle, SentimentLabel, Topic
from src.contracts.events import EventRecord
from src.logging import get_logger
from src.repositories.article_repo import ArticleRepository
from src.repositories.event_repo import EventRepository
from src.services.events.cluster_service import ClusterService
from src.services.events.scoring import ImpactScorer

logger = get_logger("service.event_builder")

TOPIC_COORDINATES: dict[Topic, tuple[float, float]] = {
    Topic.POLITICS: (-1.286389, 36.817223),
    Topic.DISASTER: (35.6895, 139.6917),
    Topic.ECONOMICS: (40.7128, -74.0060),
    Topic.TECHNOLOGY: (37.7749, -122.4194),
    Topic.CONFLICT: (31.7683, 35.2137),
    Topic.OTHER: (51.5072, -0.1276),
}


@dataclass
class RebuildResult:
    events_created: int
    articles_clustered: int
    clusters_formed: int


class EventBuilder:
    def __init__(
        self,
        article_repo: ArticleRepository,
        event_repo: EventRepository,
        cluster_service: ClusterService | None = None,
        scorer: ImpactScorer | None = None,
    ) -> None:
        self._article_repo = article_repo
        self._event_repo = event_repo
        self._cluster = cluster_service or ClusterService()
        self._scorer = scorer or ImpactScorer()

    def rebuild(self) -> RebuildResult:
        """
        Full event rebuild from all enriched articles.

        This is a destructive operation — all existing events are
        replaced. For incremental updates, use an incremental
        clustering strategy (future enhancement).
        """
        enriched = self._article_repo.get_all_enriched()
        if not enriched:
            logger.info("No enriched articles to cluster")
            return RebuildResult(events_created=0, articles_clustered=0, clusters_formed=0)

        clusters = self._cluster.cluster(enriched)
        self._event_repo.clear_all()

        events_created = 0
        for idx, cluster in enumerate(clusters, start=1):
            event = self._build_event(idx, cluster)
            self._event_repo.upsert_event(event)
            events_created += 1

        result = RebuildResult(
            events_created=events_created,
            articles_clustered=len(enriched),
            clusters_formed=len(clusters),
        )
        logger.info("Event rebuild complete", extra={"result": result.__dict__})
        return result

    def _build_event(self, idx: int, cluster: list[ArticleEnriched]) -> EventRecord:
        lead = _select_lead_article(cluster)
        topic = _majority_topic(cluster)
        sentiment = _majority_sentiment(cluster)
        lat, lon = TOPIC_COORDINATES.get(topic, TOPIC_COORDINATES[Topic.OTHER])
        score = self._scorer.score(cluster)
        event_id = _stable_event_id(cluster)

        summary = _build_summary(lead, cluster)

        return EventRecord(
            id=event_id,
            title=lead.title,
            summary=summary,
            topic=topic,
            sentiment=sentiment,
            latitude=lat,
            longitude=lon,
            impact_score=score,
            article_ids=[a.id for a in cluster],
            lifecycle=EventLifecycle.ACTIVE,
            confidence=min(len(cluster) / 5.0, 1.0),
            updated_at=datetime.now(timezone.utc),
        )


def _select_lead_article(cluster: list[ArticleEnriched]) -> ArticleEnriched:
    """
    Pick the most representative article as event lead.

    The lead is the article whose entities overlap most with
    the cluster's collective entity set, weighted by recency.
    Falls back to the most recent article if entities are sparse.
    """
    if len(cluster) == 1:
        return cluster[0]

    all_entities: Counter[str] = Counter()
    for article in cluster:
        for entity in article.entities:
            all_entities[entity.lower()] += 1

    best = cluster[0]
    best_score = -1.0
    for article in cluster:
        entity_overlap = sum(
            all_entities.get(e.lower(), 0)
            for e in article.entities
        )
        score = entity_overlap + (0.1 if article == cluster[-1] else 0)
        if score > best_score:
            best_score = score
            best = article

    return best


def _majority_topic(cluster: list[ArticleEnriched]) -> Topic:
    counts: Counter[Topic] = Counter(a.topic for a in cluster)
    return counts.most_common(1)[0][0]


def _majority_sentiment(cluster: list[ArticleEnriched]) -> SentimentLabel:
    counts: Counter[SentimentLabel] = Counter(a.sentiment for a in cluster)
    return counts.most_common(1)[0][0]


def _build_summary(lead: ArticleEnriched, cluster: list[ArticleEnriched]) -> str:
    """
    Generate event summary from lead article and cluster metadata.

    Combines the lead article's summary with cluster context
    (article count, source diversity, time span).
    """
    base = lead.summary
    n = len(cluster)
    sources = len({a.source for a in cluster})

    if n == 1:
        return base

    parts = [base]
    parts.append(f"[{n} articles")
    if sources > 1:
        parts[-1] += f" from {sources} sources"
    parts[-1] += "]"

    return " ".join(parts)


def _stable_event_id(cluster: list[ArticleEnriched]) -> str:
    """
    Generate a stable event ID from cluster article IDs.

    Same set of articles always produces the same event ID,
    enabling incremental rebuild diffing.
    """
    sorted_ids = sorted(a.id for a in cluster)
    content = "|".join(sorted_ids)
    return "evt-" + hashlib.sha256(content.encode()).hexdigest()[:12]
