from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Topic = Literal["politics", "disaster", "technology", "economics", "conflict", "other"]
SentimentLabel = Literal["positive", "neutral", "negative"]


class ArticleIn(BaseModel):
    source: str
    url: str
    title: str
    body: str
    published_at: datetime
    language: str = "en"


class ArticleEnriched(BaseModel):
    id: str
    summary: str
    topic: Topic
    sentiment: SentimentLabel
    entities: list[str]
    embedding: list[float] = Field(default_factory=list)


class Event(BaseModel):
    id: str
    title: str
    summary: str
    topic: Topic
    sentiment: SentimentLabel
    latitude: float
    longitude: float
    impact_score: float
    article_ids: list[str]
    updated_at: datetime
