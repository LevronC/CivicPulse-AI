"""Tests for shared contract validation — the schema safety net."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.contracts.articles import ArticleCreate, EnrichmentResult
from src.contracts.enums import EventLifecycle, SentimentLabel, Topic
from src.contracts.events import EventRecord
from src.contracts.pagination import PaginationParams


class TestArticleCreate:
    def test_valid_article(self) -> None:
        article = ArticleCreate(
            source="newsapi",
            url="https://example.com/article",
            title="Test Title",
            body="Test body content",
            published_at=datetime.now(timezone.utc),
        )
        assert article.language == "en"

    def test_rejects_naive_datetime(self) -> None:
        with pytest.raises(ValidationError):
            ArticleCreate(
                source="newsapi",
                url="https://example.com/article",
                title="Test",
                body="Body",
                published_at=datetime.now(),
            )

    def test_rejects_empty_source(self) -> None:
        with pytest.raises(ValidationError):
            ArticleCreate(
                source="",
                url="https://example.com/article",
                title="Test",
                body="Body",
                published_at=datetime.now(timezone.utc),
            )


class TestEnrichmentResult:
    def test_partial_enrichment_allowed(self) -> None:
        result = EnrichmentResult(summary="Test", topic=None, sentiment=None)
        assert result.topic is None
        assert result.entities == []

    def test_full_enrichment(self) -> None:
        result = EnrichmentResult(
            summary="Summary",
            topic=Topic.POLITICS,
            sentiment=SentimentLabel.NEGATIVE,
            entities=["Entity1"],
            embedding=[0.1, 0.2],
        )
        assert result.topic == Topic.POLITICS


class TestEventRecord:
    def test_latitude_bounds(self) -> None:
        with pytest.raises(ValidationError):
            EventRecord(
                id="evt-1",
                title="T",
                summary="S",
                topic=Topic.OTHER,
                sentiment=SentimentLabel.NEUTRAL,
                latitude=91.0,
                longitude=0.0,
                impact_score=50.0,
                article_ids=[],
                updated_at=datetime.now(timezone.utc),
            )

    def test_impact_score_bounds(self) -> None:
        with pytest.raises(ValidationError):
            EventRecord(
                id="evt-1",
                title="T",
                summary="S",
                topic=Topic.OTHER,
                sentiment=SentimentLabel.NEUTRAL,
                latitude=0.0,
                longitude=0.0,
                impact_score=101.0,
                article_ids=[],
                updated_at=datetime.now(timezone.utc),
            )


class TestPaginationParams:
    def test_defaults(self) -> None:
        p = PaginationParams()
        assert p.offset == 0
        assert p.limit == 20

    def test_rejects_negative_offset(self) -> None:
        with pytest.raises(ValidationError):
            PaginationParams(offset=-1)

    def test_rejects_overlimit(self) -> None:
        with pytest.raises(ValidationError):
            PaginationParams(limit=101)


class TestEventLifecycle:
    def test_all_states(self) -> None:
        assert set(EventLifecycle) == {"draft", "active", "stale", "archived", "merged"}
