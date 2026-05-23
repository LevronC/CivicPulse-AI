from __future__ import annotations

"""Shared similarity utilities for the event graph."""

import numpy as np


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    va = np.array(a, dtype=np.float64)
    vb = np.array(b, dtype=np.float64)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def update_centroid(
    current: list[float], current_count: int, new_embedding: list[float]
) -> list[float]:
    """Incremental mean centroid, L2-normalized."""
    if not new_embedding:
        return current
    if not current or current_count == 0:
        norm = float(np.linalg.norm(new_embedding))
        return (np.array(new_embedding) / norm).tolist() if norm > 0 else new_embedding

    total = np.array(current, dtype=np.float64) * current_count + np.array(
        new_embedding, dtype=np.float64
    )
    centroid = total / (current_count + 1)
    norm = float(np.linalg.norm(centroid))
    return (centroid / norm).tolist() if norm > 0 else centroid.tolist()


def entity_overlap(set_a: set[str], set_b: set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def embedding_variance(embeddings: list[list[float]]) -> float:
    """Average pairwise distance — high variance suggests split candidate."""
    if len(embeddings) < 2:
        return 0.0
    sims = []
    for i in range(len(embeddings)):
        for j in range(i + 1, len(embeddings)):
            sims.append(cosine_similarity(embeddings[i], embeddings[j]))
    if not sims:
        return 0.0
    return 1.0 - float(np.mean(sims))
