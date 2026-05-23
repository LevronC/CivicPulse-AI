from __future__ import annotations

"""
Topic-aware article clustering with temporal decay.

Groups articles into event clusters using three signals:
  1. Topic pre-grouping — articles in different topic categories
     never cluster together, preventing cross-domain pollution
  2. Embedding cosine similarity — semantic similarity between
     article text and cluster centroid
  3. Temporal proximity — articles published far apart receive a
     similarity penalty, modeling the observation that the same
     real-world event rarely spans more than 72 hours

The centroid is the running mean of all cluster member embeddings,
not just the lead article. This produces more stable cluster
assignments as articles accumulate.
"""

from collections import defaultdict
from datetime import datetime

import numpy as np

from src.contracts.articles import ArticleEnriched
from src.contracts.enums import Topic
from src.logging import get_logger

logger = get_logger("service.cluster")

_HOURS_48 = 48.0 * 3600.0


class ClusterService:
    def __init__(
        self,
        similarity_threshold: float = 0.40,
        temporal_decay_hours: float = 48.0,
    ) -> None:
        self._threshold = similarity_threshold
        self._decay_seconds = temporal_decay_hours * 3600.0

    def cluster(self, articles: list[ArticleEnriched]) -> list[list[ArticleEnriched]]:
        if not articles:
            return []

        by_topic: dict[Topic, list[ArticleEnriched]] = defaultdict(list)
        for article in articles:
            by_topic[article.topic].append(article)

        all_clusters: list[list[ArticleEnriched]] = []
        for topic, topic_articles in by_topic.items():
            topic_clusters = self._cluster_within_topic(topic_articles)
            all_clusters.extend(topic_clusters)

        all_clusters.sort(key=lambda c: len(c), reverse=True)

        logger.info(
            "Clustering complete",
            extra={
                "articles": len(articles),
                "clusters": len(all_clusters),
                "threshold": self._threshold,
                "topics": len(by_topic),
            },
        )
        return all_clusters

    def _cluster_within_topic(
        self, articles: list[ArticleEnriched]
    ) -> list[list[ArticleEnriched]]:
        """Cluster articles that share the same topic classification."""

        articles_sorted = sorted(articles, key=lambda a: a.published_at)

        clusters: list[_Cluster] = []

        for article in articles_sorted:
            if not article.embedding:
                clusters.append(_Cluster(article))
                continue

            best_cluster: _Cluster | None = None
            best_score = -1.0

            for cluster in clusters:
                raw_sim = _cosine_similarity(article.embedding, cluster.centroid)
                temporal_penalty = self._temporal_penalty(
                    article.published_at, cluster.latest_time
                )
                adjusted_sim = raw_sim * temporal_penalty

                if adjusted_sim >= self._threshold and adjusted_sim > best_score:
                    best_score = adjusted_sim
                    best_cluster = cluster

            if best_cluster is not None:
                best_cluster.add(article)
            else:
                clusters.append(_Cluster(article))

        return [c.articles for c in clusters]

    def _temporal_penalty(self, t1: datetime, t2: datetime) -> float:
        """
        Penalize similarity for articles published far apart.

        Returns 1.0 for same-time articles, decays exponentially
        to ~0.5 at the configured decay window (default 48h).
        Articles beyond 2x the decay window get heavy penalty.
        """
        delta = abs((t1 - t2).total_seconds())
        if delta <= 0:
            return 1.0
        return float(np.exp(-0.693 * delta / self._decay_seconds))


class _Cluster:
    """Internal cluster state with running centroid computation."""

    def __init__(self, seed: ArticleEnriched) -> None:
        self.articles: list[ArticleEnriched] = [seed]
        self._embedding_sum = np.array(seed.embedding, dtype=np.float64)
        self._count = 1
        self.latest_time = seed.published_at

    @property
    def centroid(self) -> list[float]:
        if self._count == 0:
            return []
        centroid = self._embedding_sum / self._count
        norm = float(np.linalg.norm(centroid))
        if norm > 0:
            centroid = centroid / norm
        return centroid.tolist()

    def add(self, article: ArticleEnriched) -> None:
        self.articles.append(article)
        if article.embedding:
            self._embedding_sum += np.array(article.embedding, dtype=np.float64)
            self._count += 1
        if article.published_at > self.latest_time:
            self.latest_time = article.published_at


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a)
    vb = np.array(b)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)
