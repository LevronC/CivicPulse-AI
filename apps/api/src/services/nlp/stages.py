from __future__ import annotations

"""
NLP enrichment stages.

Each stage is a self-contained unit with explicit input/output contracts.
Stages are designed to fail independently — if sentiment analysis fails,
summarization results are still preserved. This partial-failure tolerance
prevents a single provider outage from blocking the entire pipeline.

Current implementation uses keyword heuristics. Each stage can be
replaced with a model-based implementation by swapping the class
without changing the orchestration layer.
"""

from abc import ABC, abstractmethod
from collections import Counter

import numpy as np

from src.contracts.enums import SentimentLabel, Topic
from src.logging import get_logger

logger = get_logger("nlp.stages")


class EnrichmentStage(ABC):
    """Protocol for enrichment pipeline stages."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def process(self, text: str) -> dict:
        ...


class SummarizationStage(EnrichmentStage):
    @property
    def name(self) -> str:
        return "summarization"

    def process(self, text: str, *, max_words: int = 30) -> dict:
        words = text.split()
        if len(words) <= max_words:
            summary = text
        else:
            summary = " ".join(words[:max_words]) + "..."
        return {"summary": summary}


class TopicClassificationStage(EnrichmentStage):
    """
    Keyword-frequency topic classifier.

    Favors precision over recall — an article is only classified
    into a topic if at least one topic keyword appears. Ties are
    broken by keyword count, falling back to "other" on zero matches.
    """

    KEYWORDS: dict[Topic, set[str]] = {
        Topic.POLITICS: {"parliament", "election", "minister", "policy", "protest", "vote", "legislation"},
        Topic.DISASTER: {"earthquake", "flood", "wildfire", "hurricane", "evacuation", "tsunami", "quake"},
        Topic.TECHNOLOGY: {"ai", "startup", "chip", "software", "platform", "semiconductor", "algorithm"},
        Topic.ECONOMICS: {"market", "inflation", "stocks", "trade", "gdp", "recession", "growth"},
        Topic.CONFLICT: {"military", "strike", "attack", "border", "ceasefire", "troops", "weapons"},
    }

    @property
    def name(self) -> str:
        return "topic_classification"

    def process(self, text: str) -> dict:
        lower = text.lower()
        counts: Counter[Topic] = Counter()
        for topic, keywords in self.KEYWORDS.items():
            counts[topic] = sum(1 for kw in keywords if kw in lower)

        best_topic, best_count = counts.most_common(1)[0]
        return {"topic": best_topic if best_count > 0 else Topic.OTHER}


class SentimentStage(EnrichmentStage):
    NEGATIVE_SIGNALS = frozenset({
        "violence", "tear gas", "crisis", "death", "attack",
        "killed", "destruction", "damage", "casualties",
    })
    POSITIVE_SIGNALS = frozenset({
        "agreement", "relief", "aid", "growth", "stabilized",
        "breakthrough", "success", "recovery", "cooperation",
    })

    @property
    def name(self) -> str:
        return "sentiment"

    def process(self, text: str) -> dict:
        lower = text.lower()
        neg = sum(1 for w in self.NEGATIVE_SIGNALS if w in lower)
        pos = sum(1 for w in self.POSITIVE_SIGNALS if w in lower)

        if neg > pos:
            label = SentimentLabel.NEGATIVE
        elif pos > neg:
            label = SentimentLabel.POSITIVE
        else:
            label = SentimentLabel.NEUTRAL
        return {"sentiment": label}


class EntityExtractionStage(EnrichmentStage):
    """
    Naive NER using title-case heuristic.

    Extracts capitalized tokens as candidate entities. This is a
    placeholder — production deployment should use a proper NER model
    for multi-language support and entity type classification.
    """

    @property
    def name(self) -> str:
        return "entity_extraction"

    def process(self, text: str) -> dict:
        entities = []
        seen: set[str] = set()
        for token in text.split():
            clean = token.strip(".,;:!?\"'()[]")
            if clean and clean[0].isupper() and clean.lower() not in seen:
                entities.append(clean)
                seen.add(clean.lower())
            if len(entities) >= 15:
                break
        return {"entities": entities}


class EmbeddingStage(EnrichmentStage):
    """
    Deterministic character-frequency embedding.

    Produces a fixed-dimension unit vector from character byte values.
    Deterministic for the same input, enabling stable clustering
    across pipeline reruns. Production deployment should use a
    proper sentence-transformer model.
    """

    def __init__(self, dims: int = 32) -> None:
        self._dims = dims

    @property
    def name(self) -> str:
        return "embedding"

    def process(self, text: str) -> dict:
        vector = np.zeros(self._dims)
        for idx, byte_val in enumerate(text.encode("utf-8")):
            vector[idx % self._dims] += float(byte_val) / 255.0
        norm = float(np.linalg.norm(vector)) or 1.0
        return {"embedding": (vector / norm).tolist()}
