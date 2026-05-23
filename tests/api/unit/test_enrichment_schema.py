"""Tests for the enhanced EnrichmentResult schema with metadata."""

from datetime import datetime, timezone

from src.contracts.articles import EnrichmentResult, StageMetadata
from src.contracts.enums import SentimentLabel, Topic


def test_enrichment_result_defaults():
    result = EnrichmentResult()
    assert result.summary is None
    assert result.topic is None
    assert result.stages_succeeded == 0
    assert result.stages_failed == 0
    assert result.total_latency_ms == 0.0
    assert result.stage_metadata == []


def test_enrichment_result_with_stages():
    result = EnrichmentResult(
        summary="Test summary",
        topic=Topic.POLITICS,
        sentiment=SentimentLabel.NEUTRAL,
        entities=["Washington"],
        embedding=[0.1] * 32,
        stages_succeeded=5,
        stages_failed=0,
        total_latency_ms=42.5,
        processed_at=datetime.now(timezone.utc),
        stage_metadata=[
            StageMetadata(
                stage_name="summarization",
                model_name="heuristic",
                confidence=1.0,
                latency_ms=5.3,
            ),
            StageMetadata(
                stage_name="sentiment",
                model_name="distilbert-sentiment",
                model_version="v2",
                confidence=0.92,
                latency_ms=15.1,
            ),
        ],
    )
    assert result.stages_succeeded == 5
    assert len(result.stage_metadata) == 2
    assert result.avg_confidence == (1.0 + 0.92) / 2
    assert not result.is_partial


def test_partial_enrichment():
    result = EnrichmentResult(
        summary="Partial result",
        stages_succeeded=3,
        stages_failed=2,
    )
    assert result.is_partial


def test_stage_metadata_model_config():
    meta = StageMetadata(
        stage_name="test",
        model_name="my-model",
        model_version="v3",
        confidence=0.85,
    )
    assert meta.model_name == "my-model"
    assert meta.model_version == "v3"
    dumped = meta.model_dump()
    assert "model_name" in dumped
    assert "model_version" in dumped


def test_enrichment_result_serialization():
    result = EnrichmentResult(
        summary="Test",
        topic=Topic.TECHNOLOGY,
        sentiment=SentimentLabel.POSITIVE,
        entities=["AI", "Chip"],
        embedding=[0.5] * 32,
        enrichment_version="transformer-v1",
        stages_succeeded=5,
        processed_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        stage_metadata=[
            StageMetadata(
                stage_name="embedding",
                model_name="all-MiniLM-L6-v2",
                confidence=1.0,
                latency_ms=25.0,
            ),
        ],
    )
    data = result.model_dump()
    assert data["enrichment_version"] == "transformer-v1"
    assert len(data["stage_metadata"]) == 1
    assert data["stage_metadata"][0]["model_name"] == "all-MiniLM-L6-v2"
