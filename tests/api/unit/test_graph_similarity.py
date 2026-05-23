"""Unit tests for graph similarity utilities."""

import numpy as np

from src.services.graph.similarity import (
    cosine_similarity,
    embedding_variance,
    entity_overlap,
    update_centroid,
)


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert cosine_similarity(v, v) == 1.0

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1, 0], [0, 1]) == 0.0

    def test_empty_vectors(self):
        assert cosine_similarity([], [1, 2]) == 0.0


class TestUpdateCentroid:
    def test_first_embedding(self):
        e = [3.0, 4.0]
        result = update_centroid([], 0, e)
        assert abs(np.linalg.norm(result) - 1.0) < 0.01

    def test_incremental_update(self):
        e1 = [1.0, 0.0]
        e2 = [0.0, 1.0]
        c1 = update_centroid([], 0, e1)
        c2 = update_centroid(c1, 1, e2)
        assert len(c2) == 2


class TestEntityOverlap:
    def test_full_overlap(self):
        assert entity_overlap({"a", "b"}, {"a", "b"}) == 1.0

    def test_no_overlap(self):
        assert entity_overlap({"a"}, {"b"}) == 0.0

    def test_partial_overlap(self):
        assert entity_overlap({"a", "b"}, {"b", "c"}) == 1 / 3


class TestEmbeddingVariance:
    def test_identical_embeddings_low_variance(self):
        e = [1.0, 0.0, 0.0]
        assert embedding_variance([e, e, e]) == 0.0

    def test_diverse_embeddings_high_variance(self):
        e1 = [1.0, 0.0]
        e2 = [0.0, 1.0]
        assert embedding_variance([e1, e2]) > 0.5
