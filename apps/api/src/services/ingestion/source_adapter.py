from __future__ import annotations

"""
Source adapter interface and implementations.

Each news source (NewsAPI, GDELT, RSS, etc.) gets its own adapter
that normalizes raw source data into ArticleCreate contracts.
New sources are added by implementing the SourceAdapter protocol
without modifying any existing code.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from src.contracts.articles import ArticleCreate


class SourceAdapter(ABC):
    """Protocol for source connectors."""

    @abstractmethod
    def fetch(self) -> list[ArticleCreate]:
        """Fetch and normalize articles from the source."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        ...


class MockSourceAdapter(SourceAdapter):
    """
    Development/testing adapter that returns deterministic sample articles.

    In production this is replaced by real source adapters (NewsAPI, GDELT).
    The mock adapter exercises the full pipeline end-to-end without
    requiring external API credentials.
    """

    @property
    def source_name(self) -> str:
        return "mock"

    def fetch(self) -> list[ArticleCreate]:
        now = datetime.now(timezone.utc)
        return [
            ArticleCreate(
                source="newsapi",
                url="https://example.com/politics-tax-protest",
                title="Demonstrations rise over new tax policy",
                body=(
                    "Thousands gathered near parliament as lawmakers "
                    "introduced a new tax bill that would affect middle-income "
                    "households. Protests have been escalating throughout the week."
                ),
                published_at=now - timedelta(minutes=5),
            ),
            ArticleCreate(
                source="gdelt",
                url="https://example.com/earthquake-update",
                title="Regional authorities respond to moderate earthquake",
                body=(
                    "Emergency teams were dispatched after a 5.8 magnitude "
                    "quake hit coastal communities. Initial reports indicate "
                    "structural damage to several buildings in the port district."
                ),
                published_at=now - timedelta(minutes=11),
            ),
            ArticleCreate(
                source="newsapi",
                url="https://example.com/ai-chip-breakthrough",
                title="New AI chip design promises 10x efficiency gains",
                body=(
                    "A semiconductor startup unveiled a novel chip architecture "
                    "optimized for large language model inference. Industry "
                    "analysts predict significant cost reductions for AI deployment."
                ),
                published_at=now - timedelta(minutes=8),
            ),
        ]
