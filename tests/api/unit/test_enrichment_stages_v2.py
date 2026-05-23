"""Tests for V2 enrichment stages with model manager integration."""

from src.services.enrichment.models.manager import ModelManager
from src.services.enrichment.models.heuristic import (
    heuristic_embedding_backend,
    heuristic_entity_backend,
    heuristic_sentiment_backend,
    heuristic_summarization_backend,
    heuristic_topic_backend,
)
from src.services.enrichment.stages import (
    EmbeddingStageV2,
    EntityStageV2,
    SentimentStageV2,
    SummarizationStageV2,
    TopicStageV2,
)


def _make_manager() -> ModelManager:
    mgr = ModelManager()
    mgr.register("summarization", lambda: heuristic_summarization_backend)
    mgr.register("topic_classification", lambda: heuristic_topic_backend)
    mgr.register("sentiment", lambda: heuristic_sentiment_backend)
    mgr.register("entity_extraction", lambda: heuristic_entity_backend)
    mgr.register("embedding", lambda: heuristic_embedding_backend)
    return mgr


def test_summarization_stage():
    mgr = _make_manager()
    stage = SummarizationStageV2(mgr)
    result = stage.process("This is a short text for summarization")
    assert result.outputs["summary"]
    assert result.confidence > 0
    assert result.latency_ms >= 0
    assert stage.name == "summarization"
    assert stage.requires_model is True


def test_topic_stage():
    mgr = _make_manager()
    stage = TopicStageV2(mgr)
    result = stage.process("Parliament voted on the new election legislation")
    assert result.outputs["topic"] is not None
    assert result.confidence > 0


def test_sentiment_stage():
    mgr = _make_manager()
    stage = SentimentStageV2(mgr)
    result = stage.process("The attack caused massive destruction and casualties")
    assert result.outputs["sentiment"].value == "negative"
    assert result.confidence > 0


def test_entity_stage():
    mgr = _make_manager()
    stage = EntityStageV2(mgr)
    result = stage.process("John Smith visited Washington DC and spoke with Angela Merkel")
    entities = result.outputs["entities"]
    assert len(entities) > 0
    assert result.confidence > 0


def test_embedding_stage():
    mgr = _make_manager()
    stage = EmbeddingStageV2(mgr)
    result = stage.process("Test embedding generation")
    embedding = result.outputs["embedding"]
    assert len(embedding) == 32
    assert result.confidence == 1.0


def test_stage_result_has_provenance():
    mgr = _make_manager()
    stage = SummarizationStageV2(mgr)
    result = stage.process("Some text to process")
    assert result.model_name == "summarization"
    assert result.timestamp is not None
