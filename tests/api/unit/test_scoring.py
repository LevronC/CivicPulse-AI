"""Tests for event impact scoring logic."""

from datetime import datetime, timezone

from src.contracts.articles import ArticleEnriched
from src.contracts.enums import SentimentLabel, Topic
from src.services.events.scoring import ImpactScorer, ScoreWeights


def _make_article(
    source: str = "test",
    sentiment: SentimentLabel = SentimentLabel.NEUTRAL,
    topic: Topic = Topic.OTHER,
) -> ArticleEnriched:
    now = datetime.now(timezone.utc)
    return ArticleEnriched(
        id=f"art-{source}-{id(source)}",
        source=source,
        url=f"https://example.com/{source}",
        title="Test article",
        body="Test body",
        published_at=now,
        language="en",
        inserted_at=now,
        summary="Test summary",
        topic=topic,
        sentiment=sentiment,
        entities=[],
        embedding=[],
        enriched_at=now,
    )


class TestImpactScorer:
    def test_empty_cluster_returns_zero(self) -> None:
        scorer = ImpactScorer()
        assert scorer.score([]) == 0.0

    def test_single_article_score(self) -> None:
        scorer = ImpactScorer()
        score = scorer.score([_make_article()])
        assert 0 < score <= 100

    def test_more_articles_higher_score(self) -> None:
        scorer = ImpactScorer()
        small = scorer.score([_make_article()])
        large = scorer.score([_make_article(source=f"s{i}") for i in range(5)])
        assert large > small

    def test_negative_sentiment_boosts_score(self) -> None:
        scorer = ImpactScorer()
        neutral = scorer.score([_make_article(sentiment=SentimentLabel.NEUTRAL)])
        negative = scorer.score([_make_article(sentiment=SentimentLabel.NEGATIVE)])
        assert negative > neutral

    def test_score_capped_at_100(self) -> None:
        scorer = ImpactScorer()
        cluster = [
            _make_article(source=f"s{i}", sentiment=SentimentLabel.NEGATIVE)
            for i in range(20)
        ]
        assert scorer.score(cluster) <= 100.0

    def test_source_diversity_increases_score(self) -> None:
        scorer = ImpactScorer()
        same_source = [_make_article(source="a") for _ in range(3)]
        diverse = [_make_article(source=f"s{i}") for i in range(3)]
        assert scorer.score(diverse) > scorer.score(same_source)

    def test_explain_returns_breakdown(self) -> None:
        scorer = ImpactScorer()
        cluster = [_make_article(), _make_article(source="other")]
        explanation = scorer.explain(cluster)
        assert "article_count" in explanation
        assert "final_score" in explanation
        assert explanation["article_count"] == 2


class TestScoreWeightsCustomization:
    def test_custom_weights(self) -> None:
        heavy_negative = ScoreWeights(negative_boost=50.0)
        scorer = ImpactScorer(weights=heavy_negative)
        cluster = [_make_article(sentiment=SentimentLabel.NEGATIVE)]
        score = scorer.score(cluster)
        assert score >= 50.0
