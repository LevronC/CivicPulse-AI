from __future__ import annotations

"""
Impact scoring for event clusters.

The score is a weighted composite of three signals:
  1. Volume (article count) — capped at 10 articles = max contribution
  2. Source diversity — more diverse sources = higher credibility
  3. Negative signal boost — negative events are surfaced more
     aggressively because they typically require faster analyst response

Score range: 0..100
Calibration: the weights were chosen for the initial release.
A weekly calibration loop should adjust weights based on analyst
feedback and score distribution analysis.
"""

from dataclasses import dataclass

from src.contracts.articles import ArticleEnriched
from src.contracts.enums import SentimentLabel


@dataclass(frozen=True)
class ScoreWeights:
    """Tunable scoring parameters."""

    volume_weight: float = 40.0
    volume_cap: int = 10
    diversity_weight: float = 10.0
    negative_boost: float = 15.0


class ImpactScorer:
    def __init__(self, weights: ScoreWeights | None = None) -> None:
        self._w = weights or ScoreWeights()

    def score(self, cluster: list[ArticleEnriched]) -> float:
        if not cluster:
            return 0.0

        volume_score = min(len(cluster) / self._w.volume_cap, 1.0) * self._w.volume_weight

        unique_sources = {a.source for a in cluster}
        diversity_score = len(unique_sources) * self._w.diversity_weight

        has_negative = any(a.sentiment == SentimentLabel.NEGATIVE for a in cluster)
        negative_score = self._w.negative_boost if has_negative else 0.0

        raw = volume_score + diversity_score + negative_score
        return round(min(raw, 100.0), 2)

    def explain(self, cluster: list[ArticleEnriched]) -> dict:
        """Return scoring breakdown for explainability."""
        unique_sources = {a.source for a in cluster}
        has_negative = any(a.sentiment == SentimentLabel.NEGATIVE for a in cluster)
        return {
            "article_count": len(cluster),
            "unique_sources": len(unique_sources),
            "sources": list(unique_sources),
            "has_negative_signal": has_negative,
            "volume_contribution": min(len(cluster) / self._w.volume_cap, 1.0) * self._w.volume_weight,
            "diversity_contribution": len(unique_sources) * self._w.diversity_weight,
            "negative_boost": self._w.negative_boost if has_negative else 0.0,
            "final_score": self.score(cluster),
        }
