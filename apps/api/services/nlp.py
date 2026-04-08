from collections import Counter
from typing import Any

import numpy as np

from models import SentimentLabel, Topic

TOPIC_KEYWORDS: dict[Topic, set[str]] = {
    "politics": {"parliament", "election", "minister", "policy", "protest"},
    "disaster": {"earthquake", "flood", "wildfire", "hurricane", "evacuation"},
    "technology": {"ai", "startup", "chip", "software", "platform"},
    "economics": {"market", "inflation", "stocks", "trade", "gdp"},
    "conflict": {"military", "strike", "attack", "border", "ceasefire"},
    "other": set(),
}


def summarize(text: str, max_words: int = 30) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


def classify_topic(text: str) -> Topic:
    t = text.lower()
    counts = Counter({k: 0 for k in TOPIC_KEYWORDS})
    for topic, keywords in TOPIC_KEYWORDS.items():
        counts[topic] += sum(1 for kw in keywords if kw in t)
    best = max(counts, key=counts.get)
    return "other" if counts[best] == 0 else best


def sentiment(text: str) -> SentimentLabel:
    t = text.lower()
    if any(word in t for word in ["violence", "tear gas", "crisis", "death", "attack"]):
        return "negative"
    if any(word in t for word in ["agreement", "relief", "aid", "growth", "stabilized"]):
        return "positive"
    return "neutral"


def simple_ner(text: str) -> list[str]:
    return [token.strip(".,") for token in text.split() if token.istitle()][:10]


def embedding(text: str, dims: int = 32) -> list[float]:
    vector = np.zeros(dims)
    for idx, char in enumerate(text.encode("utf-8")):
        vector[idx % dims] += float(char) / 255.0
    norm = np.linalg.norm(vector) or 1.0
    return (vector / norm).tolist()


def enrich_article(article: dict[str, Any]) -> dict[str, Any]:
    text = f"{article['title']} {article['body']}"
    return {
        **article,
        "summary": summarize(article["body"]),
        "topic": classify_topic(text),
        "sentiment": sentiment(text),
        "entities": simple_ner(text),
        "embedding": embedding(text),
    }
