"""Tests for NLP enrichment stages — each stage is tested in isolation."""

from src.contracts.enums import SentimentLabel, Topic
from src.services.nlp.stages import (
    EmbeddingStage,
    EntityExtractionStage,
    SentimentStage,
    SummarizationStage,
    TopicClassificationStage,
)


class TestSummarizationStage:
    def test_short_text_unchanged(self) -> None:
        stage = SummarizationStage()
        result = stage.process("Short text here")
        assert result["summary"] == "Short text here"

    def test_long_text_truncated(self) -> None:
        stage = SummarizationStage()
        text = " ".join(f"word{i}" for i in range(50))
        result = stage.process(text)
        assert result["summary"].endswith("...")
        assert len(result["summary"].split()) <= 31


class TestTopicClassification:
    def test_politics_detected(self) -> None:
        stage = TopicClassificationStage()
        result = stage.process("Parliament debate on new election policy")
        assert result["topic"] == Topic.POLITICS

    def test_disaster_detected(self) -> None:
        stage = TopicClassificationStage()
        result = stage.process("Massive earthquake triggers evacuation")
        assert result["topic"] == Topic.DISASTER

    def test_unknown_returns_other(self) -> None:
        stage = TopicClassificationStage()
        result = stage.process("Random unrelated content about cooking recipes")
        assert result["topic"] == Topic.OTHER


class TestSentimentStage:
    def test_negative_signal(self) -> None:
        stage = SentimentStage()
        result = stage.process("Violence erupted and casualties were reported")
        assert result["sentiment"] == SentimentLabel.NEGATIVE

    def test_positive_signal(self) -> None:
        stage = SentimentStage()
        result = stage.process("Economic growth stabilized after agreement")
        assert result["sentiment"] == SentimentLabel.POSITIVE

    def test_neutral_default(self) -> None:
        stage = SentimentStage()
        result = stage.process("The meeting was held on Tuesday")
        assert result["sentiment"] == SentimentLabel.NEUTRAL


class TestEntityExtraction:
    def test_extracts_capitalized_tokens(self) -> None:
        stage = EntityExtractionStage()
        result = stage.process("President Biden met Chancellor Merkel in Berlin")
        entities = result["entities"]
        assert "President" in entities
        assert "Biden" in entities

    def test_deduplicates_case_insensitive(self) -> None:
        stage = EntityExtractionStage()
        result = stage.process("Berlin Berlin BERLIN")
        assert len([e for e in result["entities"] if e.lower() == "berlin"]) == 1

    def test_max_entities_capped(self) -> None:
        stage = EntityExtractionStage()
        text = " ".join(f"Entity{i}" for i in range(30))
        result = stage.process(text)
        assert len(result["entities"]) <= 15


class TestEmbeddingStage:
    def test_output_dimensions(self) -> None:
        stage = EmbeddingStage(dims=32)
        result = stage.process("Test embedding text")
        assert len(result["embedding"]) == 32

    def test_unit_vector(self) -> None:
        stage = EmbeddingStage(dims=16)
        result = stage.process("Normalize this vector")
        import numpy as np
        norm = float(np.linalg.norm(result["embedding"]))
        assert abs(norm - 1.0) < 0.01

    def test_deterministic(self) -> None:
        stage = EmbeddingStage(dims=32)
        r1 = stage.process("Same input text")
        r2 = stage.process("Same input text")
        assert r1["embedding"] == r2["embedding"]
