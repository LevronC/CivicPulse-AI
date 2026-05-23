from __future__ import annotations

"""
Entity centrality computation for event ranking.

Centrality measures how connected an event is in the entity graph:
  - local density: entities extracted from the event's articles
  - cross-event reach: how many other events share at least one entity
"""

from src.repositories.graph_repo import GraphRepository


def compute_entity_centralities(
    event_ids: list[str],
    graph_repo: GraphRepository,
) -> dict[str, float]:
    if not event_ids:
        return {}

    entity_counts = graph_repo.get_entity_counts_for_events(event_ids)
    shared_counts = graph_repo.count_shared_entity_neighbors(event_ids)

    centralities: dict[str, float] = {}
    for event_id in event_ids:
        entity_count = entity_counts.get(event_id, 0)
        shared = shared_counts.get(event_id, 0)
        local = min(entity_count / 12.0, 1.0)
        cross = min(shared / 8.0, 1.0)
        centralities[event_id] = round(local * 0.45 + cross * 0.55, 4)

    return centralities
