from __future__ import annotations

"""
Event graph service — canonical source of truth for event state.

All event creation, attachment, merging, and splitting flows through
this service. The SQL events table is a read-optimized projection
maintained by EventProjector.reconcile().
"""

from datetime import datetime, timezone

from src.config import get_settings

from src.contracts.graph import (
    BreakingStoryItem,
    EmergingEventItem,
    EntityIntelligenceResponse,
    EventEvolutionResponse,
    EventGraphNode,
    GlobalPulseResponse,
    NarrativeMapEdge,
    NarrativeMapNode,
    NarrativeMapResponse,
    ProcessResult,
    RelationshipType,
    StrengthenEdgesResult,
    TopEntityItem,
)
from src.logging import get_logger
from src.repositories.article_repo import ArticleRepository
from src.repositories.event_repo import EventRepository
from src.repositories.graph_repo import GraphRepository
from src.services.graph.centrality import compute_entity_centralities
from src.services.graph.lifecycle import EventLifecycleEngine
from src.services.graph.projector import EventProjector, ProjectionResult
from src.services.graph.ranking import EventRankingEngine
from src.services.graph.similarity_edges import SimilarityEdgeService

logger = get_logger("graph.service")


class EventGraphService:
    def __init__(
        self,
        article_repo: ArticleRepository,
        event_repo: EventRepository,
        graph_repo: GraphRepository,
        lifecycle: EventLifecycleEngine | None = None,
        ranker: EventRankingEngine | None = None,
    ) -> None:
        self._articles = article_repo
        self._events = event_repo
        self._graph = graph_repo
        self._lifecycle = lifecycle or EventLifecycleEngine(
            article_repo, event_repo, graph_repo
        )
        self._ranker = ranker or EventRankingEngine()
        self._projector = EventProjector(event_repo, graph_repo)
        self._edge_service = SimilarityEdgeService(graph_repo)

    def reconcile_projection(self) -> ProjectionResult:
        """Materialize graph truth into the events SQL projection."""
        return self._projector.reconcile()

    def _graph_only(self) -> bool:
        return get_settings().graph.graph_mode

    def process_unlinked_articles(self, limit: int = 50) -> ProcessResult:
        """
        Process enriched articles not yet linked to the event graph.

        Articles are processed in published_at order to simulate
        the streaming arrival pattern of real news feeds.
        """
        unlinked_ids = self._graph.get_unlinked_article_ids(limit=limit)
        if not unlinked_ids:
            decay_mutations = self._lifecycle.apply_decay()
            return ProcessResult(
                articles_processed=0,
                events_decayed=len(decay_mutations),
            )

        enriched = self._articles.get_all_enriched()
        by_id = {a.id: a for a in enriched}

        result = ProcessResult()
        for article_id in unlinked_ids:
            article = by_id.get(article_id)
            if article is None:
                continue
            mutations = self._lifecycle.process_article(article)
            result.articles_processed += 1
            result.mutations.extend(mutations)
            for m in mutations:
                if m.mutation_type.value == "created":
                    result.events_created += 1
                elif m.mutation_type.value == "attached":
                    result.events_updated += 1
                elif m.mutation_type.value == "merged":
                    result.events_merged += 1
                elif m.mutation_type.value == "split":
                    result.events_split += 1

        decay_mutations = self._lifecycle.apply_decay()
        result.events_decayed = len(decay_mutations)
        result.mutations.extend(decay_mutations)

        if self._graph_only():
            self.reconcile_projection()
            self.strengthen_similarity_edges()

        logger.info("Graph processing complete", extra={"result": result.model_dump()})
        return result

    def bootstrap_from_enriched(self) -> ProcessResult:
        """Process all enriched articles through the graph in time order."""
        enriched = sorted(
            self._articles.get_all_enriched(),
            key=lambda a: a.published_at,
        )
        result = ProcessResult()
        for article in enriched:
            if self._graph.is_article_linked(article.id):
                continue
            mutations = self._lifecycle.process_article(article)
            result.articles_processed += 1
            result.mutations.extend(mutations)
            for m in mutations:
                if m.mutation_type.value == "created":
                    result.events_created += 1
                elif m.mutation_type.value == "attached":
                    result.events_updated += 1
                elif m.mutation_type.value == "merged":
                    result.events_merged += 1
                elif m.mutation_type.value == "split":
                    result.events_split += 1

        decay = self._lifecycle.apply_decay()
        result.events_decayed = len(decay)
        if self._graph_only():
            self.reconcile_projection()
            self.strengthen_similarity_edges()
        return result

    def strengthen_similarity_edges(self) -> StrengthenEdgesResult:
        active = self._events.list_all_active(graph_only=self._graph_only())
        stats = self._edge_service.strengthen(active)
        return StrengthenEdgesResult(
            edges_created=stats["edges_created"],
            edges_updated=stats["edges_updated"],
            pairs_evaluated=stats["pairs_evaluated"],
        )

    def global_pulse(self, *, limit: int = 20, window_hours: float = 24.0) -> GlobalPulseResponse:
        now = datetime.now(timezone.utc)
        active = self._events.list_all_active(graph_only=self._graph_only())
        source_counts = self._compute_source_counts(active)
        centralities = compute_entity_centralities(
            [e.id for e in active], self._graph
        )
        items = self._ranker.rank_events(
            active, source_counts, centralities, now=now, limit=limit
        )
        return GlobalPulseResponse(
            items=items,
            generated_at=now,
            window_hours=window_hours,
        )

    def event_evolution(self, event_id: str) -> EventEvolutionResponse | None:
        event = self._events.get_event(event_id)
        if event is None:
            return None

        snapshots = self._graph.get_snapshots(event_id)
        related_ids = self._graph.get_related_events(event_id)
        related_events: list[EventGraphNode] = []
        for rid in related_ids:
            rel = self._events.get_event(rid)
            if rel:
                related_events.append(self._to_graph_node(rel))

        entities = self._graph.get_entities_for_event(event_id)
        return EventEvolutionResponse(
            event_id=event_id,
            snapshots=snapshots,
            related_events=related_events,
            entities=entities,
        )

    def breaking_stories(self, *, limit: int = 10) -> list[BreakingStoryItem]:
        now = datetime.now(timezone.utc)
        active = self._events.list_all_active(graph_only=self._graph_only())
        centralities = compute_entity_centralities([e.id for e in active], self._graph)
        growth = self._compute_article_growth(active)
        return self._ranker.breaking_stories(
            active, centralities, growth, now=now, limit=limit
        )

    def emerging_events(self, *, limit: int = 10) -> list[EmergingEventItem]:
        breaking = self.breaking_stories(limit=limit)
        return [
            EmergingEventItem(
                event=item.event,
                novelty_score=item.breaking_score,
                growth_rate=item.velocity,
            )
            for item in breaking
        ]

    def narrative_map(self, *, limit: int = 40) -> NarrativeMapResponse:
        now = datetime.now(timezone.utc)
        active = self._events.list_all_active(graph_only=self._graph_only())
        active = sorted(
            active,
            key=lambda e: (e.velocity, e.article_count or 0),
            reverse=True,
        )[:limit]
        centralities = compute_entity_centralities([e.id for e in active], self._graph)
        source_counts = self._compute_source_counts(active)

        nodes: list[NarrativeMapNode] = []
        active_ids = {e.id for e in active}
        for event in active:
            score = self._ranker.score_event(
                event,
                source_diversity=source_counts.get(event.id, 1),
                entity_centrality=centralities.get(event.id, 0.0),
                now=now,
            )
            nodes.append(
                NarrativeMapNode(
                    id=event.id,
                    title=event.title,
                    topic=event.topic,
                    velocity=event.velocity,
                    article_count=event.article_count or len(event.article_ids),
                    entity_centrality=centralities.get(event.id, 0.0),
                    intelligence_score=score,
                )
            )

        edges: list[NarrativeMapEdge] = []
        for edge in self._graph.list_relationships(
            relationship_type=RelationshipType.RELATED_TO, limit=500
        ):
            if edge.source_id in active_ids and edge.target_id in active_ids:
                edges.append(
                    NarrativeMapEdge(
                        source_id=edge.source_id,
                        target_id=edge.target_id,
                        relationship_type=edge.relationship_type,
                        weight=edge.weight,
                        label="related",
                    )
                )

        return NarrativeMapResponse(nodes=nodes, edges=edges, generated_at=now)

    def top_entities(self, *, limit: int = 20) -> list[TopEntityItem]:
        rows = self._graph.search_top_entities(limit=limit)
        return [
            TopEntityItem(entity=entity, event_count=event_count, total_articles=mentions)
            for entity, event_count, mentions in rows
        ]

    def entity_intelligence(self, name: str) -> EntityIntelligenceResponse | None:
        entity = self._graph.get_entity_by_name(name)
        if entity is None:
            return None

        event_ids = self._graph.get_events_for_entity(entity.normalized_name)
        centralities = compute_entity_centralities(event_ids, self._graph)
        events: list[EventGraphNode] = []
        total_articles = 0
        for eid in event_ids:
            event = self._events.get_event(eid)
            if event and event.lifecycle.value in ("active", "stale"):
                events.append(
                    self._to_graph_node(
                        event,
                        entity_centrality=centralities.get(eid, 0.0),
                    )
                )
                total_articles += event.article_count or len(event.article_ids)

        events.sort(key=lambda e: e.intelligence_score, reverse=True)
        return EntityIntelligenceResponse(
            entity=entity,
            events=events,
            total_articles=total_articles,
        )

    def _compute_article_growth(self, events: list) -> dict[str, int]:
        growth: dict[str, int] = {}
        for event in events:
            snapshots = self._graph.get_snapshots(event.id, limit=2)
            if len(snapshots) >= 2:
                growth[event.id] = snapshots[0].article_count - snapshots[1].article_count
            else:
                growth[event.id] = max((event.article_count or 1) - 1, 0)
        return growth

    def _compute_source_counts(self, events: list) -> dict[str, int]:
        enriched = self._articles.get_all_enriched()
        by_id = {a.id: a for a in enriched}
        counts: dict[str, int] = {}
        for event in events:
            sources = {by_id[aid].source for aid in event.article_ids if aid in by_id}
            counts[event.id] = len(sources) if sources else 1
        return counts

    def _to_graph_node(self, event, *, entity_centrality: float = 0.0) -> EventGraphNode:
        score = self._ranker.score_event(event, entity_centrality=entity_centrality)
        return EventGraphNode(
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
