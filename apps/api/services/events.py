from datetime import datetime, timezone
from typing import Any

import numpy as np


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a)
    vb = np.array(b)
    denom = (np.linalg.norm(va) * np.linalg.norm(vb)) or 1.0
    return float(np.dot(va, vb) / denom)


def cluster_articles(enriched: list[dict[str, Any]], threshold: float = 0.88) -> list[list[dict[str, Any]]]:
    clusters: list[list[dict[str, Any]]] = []
    for article in enriched:
        placed = False
        for cluster in clusters:
            if cosine_similarity(article["embedding"], cluster[0]["embedding"]) >= threshold:
                cluster.append(article)
                placed = True
                break
        if not placed:
            clusters.append([article])
    return clusters


def score_impact(cluster: list[dict[str, Any]]) -> float:
    count_score = min(len(cluster) / 10.0, 1.0) * 40.0
    sentiment_penalty = 15.0 if any(item["sentiment"] == "negative" for item in cluster) else 0.0
    source_diversity = len({item["source"] for item in cluster}) * 10.0
    return round(min(count_score + sentiment_penalty + source_diversity, 100.0), 2)


def to_event(idx: int, cluster: list[dict[str, Any]]) -> dict[str, Any]:
    lead = cluster[0]
    coords = {
        "politics": ( -1.286389, 36.817223),
        "disaster": (35.6895, 139.6917),
        "economics": (40.7128, -74.0060),
        "technology": (37.7749, -122.4194),
        "conflict": (31.7683, 35.2137),
        "other": (51.5072, -0.1276),
    }
    lat, lon = coords.get(lead["topic"], coords["other"])
    return {
        "id": f"evt-{idx}",
        "title": lead["title"],
        "summary": lead["summary"],
        "topic": lead["topic"],
        "sentiment": lead["sentiment"],
        "latitude": lat,
        "longitude": lon,
        "impact_score": score_impact(cluster),
        "article_ids": [item["id"] for item in cluster],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
