from __future__ import annotations

"""
Cross-event similarity edge strengthener.

Scans active events and creates or updates related_to edges based on
embedding proximity and shared entity overlap. This builds the narrative
map layer that connects distinct but related real-world stories.
"""

from dataclasses import dataclass

from src.contracts.graph import RelationshipType
from src.contracts.events import EventRecord
from src.logging import get_logger
from src.repositories.graph_repo import GraphRepository
from src.services.graph.similarity import cosine_similarity, entity_overlap

logger = get_logger("graph.similarity_edges")


@dataclass(frozen=True)
class EdgeStrengthenConfig:
    similarity_threshold: float = 0.42
    entity_overlap_threshold: float = 0.20
    same_topic_only: bool = True


class SimilarityEdgeService:
    def __init__(
        self,
        graph_repo: GraphRepository,
        config: EdgeStrengthenConfig | None = None,
    ) -> None:
        self._graph = graph_repo
        self._config = config or EdgeStrengthenConfig()

    def strengthen(self, events: list[EventRecord]) -> dict[str, int]:
        created = 0
        updated = 0
        pairs = 0

        for i, left in enumerate(events):
            if not left.centroid_embedding:
                continue
            for right in events[i + 1 :]:
                if self._config.same_topic_only and left.topic != right.topic:
                    continue
                if not right.centroid_embedding:
                    continue

                pairs += 1
                sim = cosine_similarity(left.centroid_embedding, right.centroid_embedding)
                overlap = entity_overlap(set(left.entity_set), set(right.entity_set))

                if sim < self._config.similarity_threshold and overlap < self._config.entity_overlap_threshold:
                    continue

                weight = round(sim * 0.65 + overlap * 0.35, 4)
                if self._graph.upsert_relationship(
                    left.id, right.id, RelationshipType.RELATED_TO, weight
                ):
                    created += 1
                else:
                    updated += 1

        result = {"edges_created": created, "edges_updated": updated, "pairs_evaluated": pairs}
        logger.info("Similarity edges strengthened", extra=result)
        return result
