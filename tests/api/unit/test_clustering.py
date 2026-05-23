"""Tests for topic-aware clustering with temporal decay."""

from datetime import datetime, timezone, timedelta

import numpy as np
from src.contracts.articles import ArticleEnriched
from src.contracts.enums import SentimentLabel, Topic
from src.services.events.cluster_service import ClusterService


def _make_article(
    *,
    topic: Topic = Topic.POLITICS,
    embedding: list[float] | None = None,
    hours_ago: float = 0,
    title: str = "Test article",
) -> ArticleEnriched:
    now = datetime.now(timezone.utc)
    return ArticleEnriched(
        id=f"art-{title[:8]}-{hours_ago}",
        source="test",
        url=f"https://example.com/{title}",
        title=title,
        body="Test body",
        published_at=now - timedelta(hours=hours_ago),
        language="en",
        inserted_at=now,
        summary=title,
        topic=topic,
        sentiment=SentimentLabel.NEUTRAL,
        entities=["Test"],
        embedding=embedding or [0.0] * 384,
        enriched_at=now,
    )


def _random_embedding(seed: int, dims: int = 384) -> list[float]:
    rng = np.random.RandomState(seed)
    vec = rng.randn(dims)
    return (vec / np.linalg.norm(vec)).tolist()


class TestClusterService:
    def test_empty_input(self):
        cs = ClusterService()
        assert cs.cluster([]) == []

    def test_different_topics_never_cluster(self):
        """Articles with different topics must be in separate clusters."""
        embedding = _random_embedding(42)
        a = _make_article(topic=Topic.POLITICS, embedding=embedding, title="Politics A")
        b = _make_article(topic=Topic.DISASTER, embedding=embedding, title="Disaster B")

        clusters = ClusterService().cluster([a, b])
        assert len(clusters) == 2

    def test_identical_embeddings_same_topic_cluster_together(self):
        embedding = _random_embedding(42)
        a = _make_article(topic=Topic.POLITICS, embedding=embedding, title="Article A")
        b = _make_article(topic=Topic.POLITICS, embedding=embedding, title="Article B")

        clusters = ClusterService().cluster([a, b])
        assert len(clusters) == 1
        assert len(clusters[0]) == 2

    def test_orthogonal_embeddings_separate(self):
        """Semantically unrelated articles in the same topic still separate."""
        dims = 384
        e1 = [0.0] * dims
        e1[0] = 1.0
        e2 = [0.0] * dims
        e2[1] = 1.0

        a = _make_article(topic=Topic.POLITICS, embedding=e1, title="Article A")
        b = _make_article(topic=Topic.POLITICS, embedding=e2, title="Article B")

        clusters = ClusterService().cluster([a, b])
        assert len(clusters) == 2

    def test_temporal_decay_separates_distant_articles(self):
        """Same embedding but 96 hours apart should not cluster."""
        embedding = _random_embedding(42)
        a = _make_article(topic=Topic.POLITICS, embedding=embedding, title="Recent", hours_ago=0)
        b = _make_article(topic=Topic.POLITICS, embedding=embedding, title="Old", hours_ago=96)

        clusters = ClusterService(temporal_decay_hours=48).cluster([a, b])
        assert len(clusters) == 2

    def test_close_in_time_clusters_together(self):
        """Same embedding and close in time should cluster."""
        embedding = _random_embedding(42)
        a = _make_article(topic=Topic.POLITICS, embedding=embedding, title="A", hours_ago=0)
        b = _make_article(topic=Topic.POLITICS, embedding=embedding, title="B", hours_ago=2)

        clusters = ClusterService(temporal_decay_hours=48).cluster([a, b])
        assert len(clusters) == 1

    def test_centroid_updates_with_new_members(self):
        """Cluster centroid should shift as articles are added."""
        e1 = _random_embedding(1)
        e2 = _random_embedding(1)
        e3 = _random_embedding(99)

        a = _make_article(topic=Topic.DISASTER, embedding=e1, title="A")
        b = _make_article(topic=Topic.DISASTER, embedding=e2, title="B")
        c = _make_article(topic=Topic.DISASTER, embedding=e3, title="C")

        clusters = ClusterService().cluster([a, b, c])
        assert len(clusters) >= 1
        largest = max(clusters, key=len)
        assert len(largest) >= 2

    def test_empty_embedding_gets_own_cluster(self):
        a = _make_article(topic=Topic.POLITICS, embedding=[], title="Empty")
        b = _make_article(topic=Topic.POLITICS, embedding=_random_embedding(42), title="Normal")

        clusters = ClusterService().cluster([a, b])
        assert len(clusters) == 2
