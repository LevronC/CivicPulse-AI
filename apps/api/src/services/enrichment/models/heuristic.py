from __future__ import annotations

"""
Heuristic model backends for development and CI.

These produce the same outputs as the original NLP stages but
expose them through the ModelBackend callable interface. This
allows the ModelManager to swap in transformer-backed backends
without changing any stage code.

Each backend receives text and returns a dict with the outputs
that the corresponding stage expects.
"""

from collections import Counter
from typing import Any

import numpy as np

from src.contracts.enums import SentimentLabel, Topic


def heuristic_summarization_backend(text: str, *, max_words: int = 30) -> dict[str, Any]:
    words = text.split()
    if len(words) <= max_words:
        return {"summary": text}
    return {"summary": " ".join(words[:max_words]) + "..."}


_TOPIC_KEYWORDS: dict[Topic, set[str]] = {
    Topic.POLITICS: {
        "parliament", "election", "minister", "policy", "protest", "vote",
        "legislation", "senator", "congress", "president", "governor",
        "diplomatic", "sanction", "treaty", "democrat", "republican",
        "political", "lawmaker", "ballot", "campaign",
    },
    Topic.DISASTER: {
        "earthquake", "flood", "wildfire", "hurricane", "evacuation", "tsunami",
        "quake", "disaster", "cyclone", "tornado", "volcanic", "landslide",
        "famine", "drought", "explosion", "outbreak", "ebola", "pandemic",
        "epidemic", "rescue",
    },
    Topic.TECHNOLOGY: {
        "startup", "chip", "software", "semiconductor", "algorithm",
        "artificial intelligence", "machine learning", "quantum", "robotics",
        "cryptocurrency", "blockchain", "cybersecurity", "neural network",
    },
    Topic.ECONOMICS: {
        "market", "inflation", "stocks", "trade", "gdp", "recession",
        "growth", "economy", "tariff", "export", "import", "housing",
        "interest rate", "unemployment", "deficit", "currency",
    },
    Topic.CONFLICT: {
        "military", "strike", "attack", "border", "ceasefire", "troops",
        "weapons", "war", "missile", "drone", "invasion", "combat",
        "bombing", "shelling", "artillery", "killed", "casualties",
        "airstrike", "soldier", "militia", "rebel",
    },
}


def _word_matches_keyword(word: str, keyword: str) -> bool:
    """Match keyword allowing common English suffixes (-s, -ed, -ing, -er)."""
    if word == keyword:
        return True
    return word.startswith(keyword) and len(word) - len(keyword) <= 3


def heuristic_topic_backend(text: str) -> dict[str, Any]:
    lower = text.lower()
    words = list(lower.split())
    counts: Counter[Topic] = Counter()
    for topic, keywords in _TOPIC_KEYWORDS.items():
        for kw in keywords:
            if " " in kw:
                if kw in lower:
                    counts[topic] += 1
            elif any(_word_matches_keyword(w, kw) for w in words):
                counts[topic] += 1
    if not counts:
        return {"topic": Topic.OTHER}
    best_topic, best_count = counts.most_common(1)[0]
    return {"topic": best_topic if best_count > 0 else Topic.OTHER}


_NEG_SIGNALS = frozenset({
    "violence", "tear gas", "crisis", "death", "attack",
    "killed", "destruction", "damage", "casualties",
})
_POS_SIGNALS = frozenset({
    "agreement", "relief", "aid", "growth", "stabilized",
    "breakthrough", "success", "recovery", "cooperation",
})


def heuristic_sentiment_backend(text: str) -> dict[str, Any]:
    words = set(text.lower().split())
    neg = sum(1 for w in _NEG_SIGNALS if w in words)
    pos = sum(1 for w in _POS_SIGNALS if w in words)
    if neg > pos:
        label = SentimentLabel.NEGATIVE
    elif pos > neg:
        label = SentimentLabel.POSITIVE
    else:
        label = SentimentLabel.NEUTRAL
    return {"sentiment": label}


def heuristic_entity_backend(text: str) -> dict[str, Any]:
    entities: list[str] = []
    seen: set[str] = set()
    for token in text.split():
        clean = token.strip(".,;:!?\"'()[]")
        if clean and clean[0].isupper() and clean.lower() not in seen:
            entities.append(clean)
            seen.add(clean.lower())
        if len(entities) >= 15:
            break
    return {"entities": entities}


def heuristic_embedding_backend(text: str, *, dims: int = 32) -> dict[str, Any]:
    vector = np.zeros(dims)
    for idx, byte_val in enumerate(text.encode("utf-8")):
        vector[idx % dims] += float(byte_val) / 255.0
    norm = float(np.linalg.norm(vector)) or 1.0
    return {"embedding": (vector / norm).tolist()}
