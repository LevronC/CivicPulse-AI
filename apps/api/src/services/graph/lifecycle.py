from __future__ import annotations

"""
Event lifecycle engine — the heart of Phase 4.

Replaces batch clustering with continuous graph mutations:
  - create: new article has no matching active event
  - attach: article joins existing event, centroid updates
  - merge: two events converge (shared entities + embedding proximity)
  - split: internal coherence drops, event divides into sub-events
  - decay: inactive events transition to stale/archived
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from src.contracts.articles import ArticleEnriched
from src.contracts.enums import EventLifecycle, SentimentLabel, Topic
from src.contracts.events import EventRecord
from src.contracts.graph import GraphMutation, MutationType, RelationshipType
from src.logging import get_logger
from src.repositories.article_repo import ArticleRepository
from src.repositories.event_repo import EventRepository
from src.repositories.graph_repo import GraphRepository
from src.services.events.event_builder import (
    TOPIC_COORDINATES,
    _build_summary,
    _majority_sentiment,
    _majority_topic,
    _select_lead_article,
)
from src.services.events.scoring import ImpactScorer
from src.services.graph.ranking import EventRankingEngine
from src.services.graph.similarity import (
    cosine_similarity,
    embedding_variance,
    entity_overlap,
    update_centroid,
)

logger = get_logger("graph.lifecycle")


@dataclass(frozen=True)
class LifecycleConfig:
    attach_threshold: float = 0.40
    merge_threshold: float = 0.72
    merge_entity_overlap: float = 0.25
    split_min_articles: int = 4
    split_variance_threshold: float = 0.55
    stale_hours: float = 72.0
    archive_hours: float = 168.0
    temporal_decay_hours: float = 48.0


class EventLifecycleEngine:
    def __init__(
        self,
        article_repo: ArticleRepository,
        event_repo: EventRepository,
        graph_repo: GraphRepository,
        config: LifecycleConfig | None = None,
        scorer: ImpactScorer | None = None,
        ranker: EventRankingEngine | None = None,
    ) -> None:
        self._articles = article_repo
        self._events = event_repo
        self._graph = graph_repo
        self._config = config or LifecycleConfig()
        self._scorer = scorer or ImpactScorer()
        self._ranker = ranker or EventRankingEngine()
        self._decay_seconds = self._config.temporal_decay_hours * 3600.0

    def process_article(self, article: ArticleEnriched) -> list[GraphMutation]:
        if self._graph.is_article_linked(article.id):
            return []

        mutations: list[GraphMutation] = []
        candidates = self._events.list_active_by_topic(article.topic)

        best_event: EventRecord | None = None
        best_score = -1.0

        for event in candidates:
            if not event.centroid_embedding:
                continue
            raw_sim = cosine_similarity(article.embedding, event.centroid_embedding)
            temporal = self._temporal_penalty(
                article.published_at,
                event.last_article_at or event.updated_at,
            )
            adjusted = raw_sim * temporal
            if adjusted >= self._config.attach_threshold and adjusted > best_score:
                best_score = adjusted
                best_event = event

        if best_event is not None:
            mutation = self._attach_article(best_event, article, best_score)
            mutations.append(mutation)
            merge_mutations = self._try_merge(best_event)
            mutations.extend(merge_mutations)
            split_mutations = self._try_split(best_event.id)
            mutations.extend(split_mutations)
        else:
            mutation = self._create_event(article)
            mutations.append(mutation)

        self._link_entities(article, mutations[-1].event_id)
        self._graph.link_article_event(article.id, mutations[-1].event_id, best_score if best_score > 0 else 1.0)
        return mutations

    def apply_decay(self) -> list[GraphMutation]:
        now = datetime.now(timezone.utc)
        mutations: list[GraphMutation] = []
        for event in self._events.list_all_active():
            last = event.last_article_at or event.updated_at
            hours_idle = (now - last).total_seconds() / 3600.0

            if hours_idle >= self._config.archive_hours:
                event.lifecycle = EventLifecycle.ARCHIVED
                self._events.upsert_event(event)
                mutations.append(GraphMutation(
                    mutation_type=MutationType.DECAYED,
                    event_id=event.id,
                    details={"new_lifecycle": "archived", "hours_idle": hours_idle},
                ))
            elif hours_idle >= self._config.stale_hours and event.lifecycle == EventLifecycle.ACTIVE:
                event.lifecycle = EventLifecycle.STALE
                self._events.upsert_event(event)
                mutations.append(GraphMutation(
                    mutation_type=MutationType.DECAYED,
                    event_id=event.id,
                    details={"new_lifecycle": "stale", "hours_idle": hours_idle},
                ))
        return mutations

    def _create_event(self, article: ArticleEnriched) -> GraphMutation:
        now = datetime.now(timezone.utc)
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        topic = article.topic
        lat, lon = TOPIC_COORDINATES.get(topic, TOPIC_COORDINATES[Topic.OTHER])
        cluster = [article]
        score = self._scorer.score(cluster)

        event = EventRecord(
            id=event_id,
            title=article.title,
            summary=article.summary,
            topic=topic,
            sentiment=article.sentiment,
            latitude=lat,
            longitude=lon,
            impact_score=score,
            article_ids=[article.id],
            lifecycle=EventLifecycle.ACTIVE,
            confidence=0.2,
            updated_at=now,
            centroid_embedding=list(article.embedding),
            entity_set=[e.lower() for e in article.entities],
            velocity=1.0,
            article_count=1,
            first_seen_at=article.published_at,
            last_article_at=article.published_at,
        )
        self._events.upsert_event(event)
        self._record_snapshot(event)
        logger.info("Event created", extra={"event_id": event_id, "article_id": article.id})
        return GraphMutation(
            mutation_type=MutationType.CREATED,
            event_id=event_id,
            article_id=article.id,
        )

    def _attach_article(
        self, event: EventRecord, article: ArticleEnriched, similarity: float
    ) -> GraphMutation:
        now = datetime.now(timezone.utc)
        prev_count = event.article_count or len(event.article_ids)
        articles = self._load_cluster_articles(event.article_ids + [article.id])
        lead = _select_lead_article(articles)

        hours_elapsed = max(
            (now - (event.last_article_at or event.updated_at)).total_seconds() / 3600.0,
            0.01,
        )
        new_count = prev_count + 1
        velocity = self._ranker.compute_velocity(prev_count, new_count, hours_elapsed)

        entity_set = set(event.entity_set)
        entity_set.update(e.lower() for e in article.entities)

        event.title = lead.title
        event.summary = _build_summary(lead, articles)
        event.topic = _majority_topic(articles)
        event.sentiment = _majority_sentiment(articles)
        event.article_ids = list(dict.fromkeys(event.article_ids + [article.id]))
        event.article_count = new_count
        event.centroid_embedding = update_centroid(
            event.centroid_embedding, prev_count, article.embedding
        )
        event.entity_set = sorted(entity_set)
        event.velocity = velocity
        event.impact_score = self._scorer.score(articles)
        event.confidence = min(new_count / 5.0, 1.0)
        event.last_article_at = article.published_at
        event.updated_at = now
        event.lifecycle = EventLifecycle.ACTIVE

        self._events.upsert_event(event)
        self._record_snapshot(event)
        self._update_related_events(event)

        logger.info(
            "Article attached to event",
            extra={"event_id": event.id, "article_id": article.id, "similarity": round(similarity, 3)},
        )
        return GraphMutation(
            mutation_type=MutationType.ATTACHED,
            event_id=event.id,
            article_id=article.id,
            details={"similarity": round(similarity, 3), "article_count": new_count},
        )

    def _try_merge(self, event: EventRecord) -> list[GraphMutation]:
        mutations: list[GraphMutation] = []
        if not event.centroid_embedding:
            return mutations

        event_entities = set(event.entity_set)
        for candidate in self._events.list_active_by_topic(event.topic):
            if candidate.id == event.id or not candidate.centroid_embedding:
                continue
            sim = cosine_similarity(event.centroid_embedding, candidate.centroid_embedding)
            overlap = entity_overlap(event_entities, set(candidate.entity_set))
            if sim >= self._config.merge_threshold and overlap >= self._config.merge_entity_overlap:
                mutation = self._merge_events(event, candidate, sim)
                if mutation:
                    mutations.append(mutation)
                    break
        return mutations

    def _merge_events(
        self, primary: EventRecord, secondary: EventRecord, similarity: float
    ) -> GraphMutation | None:
        if len(primary.article_ids) < len(secondary.article_ids):
            primary, secondary = secondary, primary

        now = datetime.now(timezone.utc)
        merged_ids = list(dict.fromkeys(primary.article_ids + secondary.article_ids))
        articles = self._load_cluster_articles(merged_ids)
        lead = _select_lead_article(articles)

        entity_set = set(primary.entity_set) | set(secondary.entity_set)
        primary.title = lead.title
        primary.summary = _build_summary(lead, articles)
        primary.article_ids = merged_ids
        primary.article_count = len(merged_ids)
        primary.entity_set = sorted(entity_set)
        primary.impact_score = self._scorer.score(articles)
        primary.confidence = min(len(merged_ids) / 5.0, 1.0)
        primary.updated_at = now
        primary.last_article_at = max(
            primary.last_article_at or now,
            secondary.last_article_at or now,
        )

        if primary.centroid_embedding and secondary.centroid_embedding:
            combined = np.array(primary.centroid_embedding) + np.array(secondary.centroid_embedding)
            norm = float(np.linalg.norm(combined))
            primary.centroid_embedding = (combined / norm).tolist() if norm > 0 else primary.centroid_embedding

        self._events.upsert_event(primary)
        secondary.lifecycle = EventLifecycle.MERGED
        secondary.parent_event_id = primary.id
        self._events.upsert_event(secondary)

        self._graph.add_relationship(
            primary.id, secondary.id, RelationshipType.MERGED_FROM, weight=similarity
        )
        self._record_snapshot(primary)

        logger.info(
            "Events merged",
            extra={"primary": primary.id, "secondary": secondary.id, "similarity": round(similarity, 3)},
        )
        return GraphMutation(
            mutation_type=MutationType.MERGED,
            event_id=primary.id,
            related_event_ids=[secondary.id],
            details={"similarity": round(similarity, 3)},
        )

    def _try_split(self, event_id: str) -> list[GraphMutation]:
        event = self._events.get_event(event_id)
        if event is None:
            return []

        articles = self._load_cluster_articles(event.article_ids)
        if len(articles) < self._config.split_min_articles:
            return []

        embeddings = [a.embedding for a in articles if a.embedding]
        variance = embedding_variance(embeddings)
        if variance < self._config.split_variance_threshold:
            return []

        return self._split_event(event, articles)

    def _split_event(
        self, event: EventRecord, articles: list[ArticleEnriched]
    ) -> list[GraphMutation]:
        if len(articles) < 2:
            return []

        sorted_articles = sorted(articles, key=lambda a: a.published_at)
        midpoint = len(sorted_articles) // 2
        group_a = sorted_articles[:midpoint]
        group_b = sorted_articles[midpoint:]

        inter_sim = cosine_similarity(
            group_a[0].embedding,
            group_b[0].embedding,
        )
        if inter_sim >= self._config.attach_threshold:
            return []

        now = datetime.now(timezone.utc)
        child_id = f"evt-{uuid.uuid4().hex[:12]}"
        lead_b = _select_lead_article(group_b)
        lat, lon = TOPIC_COORDINATES.get(event.topic, TOPIC_COORDINATES[Topic.OTHER])

        child = EventRecord(
            id=child_id,
            title=lead_b.title,
            summary=_build_summary(lead_b, group_b),
            topic=_majority_topic(group_b),
            sentiment=_majority_sentiment(group_b),
            latitude=lat,
            longitude=lon,
            impact_score=self._scorer.score(group_b),
            article_ids=[a.id for a in group_b],
            lifecycle=EventLifecycle.ACTIVE,
            confidence=min(len(group_b) / 5.0, 1.0),
            updated_at=now,
            centroid_embedding=_compute_centroid([a.embedding for a in group_b]),
            entity_set=sorted({e.lower() for a in group_b for e in a.entities}),
            velocity=event.velocity,
            article_count=len(group_b),
            first_seen_at=group_b[0].published_at,
            last_article_at=group_b[-1].published_at,
            parent_event_id=event.id,
        )
        self._events.upsert_event(child)

        lead_a = _select_lead_article(group_a)
        event.title = lead_a.title
        event.summary = _build_summary(lead_a, group_a)
        event.article_ids = [a.id for a in group_a]
        event.article_count = len(group_a)
        event.centroid_embedding = _compute_centroid([a.embedding for a in group_a])
        event.entity_set = sorted({e.lower() for a in group_a for e in a.entities})
        event.impact_score = self._scorer.score(group_a)
        event.updated_at = now
        self._events.upsert_event(event)

        self._graph.add_relationship(
            event.id, child_id, RelationshipType.SPLIT_FROM, weight=inter_sim
        )
        self._record_snapshot(event)
        self._record_snapshot(child)

        logger.info("Event split", extra={"parent": event.id, "child": child_id})
        return [
            GraphMutation(
                mutation_type=MutationType.SPLIT,
                event_id=event.id,
                related_event_ids=[child_id],
                details={"inter_cluster_similarity": round(inter_sim, 3)},
            )
        ]

    def _link_entities(self, article: ArticleEnriched, event_id: str) -> None:
        for name in article.entities:
            entity = self._graph.upsert_entity(name)
            self._graph.link_event_entity(event_id, entity.id)

    def _update_related_events(self, event: EventRecord) -> None:
        if not event.centroid_embedding:
            return
        for candidate in self._events.list_active_by_topic(event.topic):
            if candidate.id == event.id or not candidate.centroid_embedding:
                continue
            sim = cosine_similarity(event.centroid_embedding, candidate.centroid_embedding)
            overlap = entity_overlap(set(event.entity_set), set(candidate.entity_set))
            if sim >= 0.5 and overlap >= 0.15:
                self._graph.upsert_relationship(
                    event.id, candidate.id, RelationshipType.RELATED_TO, weight=sim
                )

    def _record_snapshot(self, event: EventRecord) -> None:
        self._graph.record_snapshot(
            event_id=event.id,
            article_count=event.article_count or len(event.article_ids),
            sentiment=event.sentiment.value,
            impact_score=event.impact_score,
            velocity=event.velocity,
            entity_set=event.entity_set,
        )

    def _load_cluster_articles(self, article_ids: list[str]) -> list[ArticleEnriched]:
        enriched = self._articles.get_all_enriched()
        by_id = {a.id: a for a in enriched}
        return [by_id[aid] for aid in article_ids if aid in by_id]

    def _temporal_penalty(self, t1: datetime, t2: datetime) -> float:
        delta = abs((t1 - t2).total_seconds())
        if delta <= 0:
            return 1.0
        return float(np.exp(-0.693 * delta / self._decay_seconds))


def _compute_centroid(embeddings: list[list[float]]) -> list[float]:
    valid = [e for e in embeddings if e]
    if not valid:
        return []
    arr = np.array(valid, dtype=np.float64)
    centroid = arr.mean(axis=0)
    norm = float(np.linalg.norm(centroid))
    return (centroid / norm).tolist() if norm > 0 else centroid.tolist()
