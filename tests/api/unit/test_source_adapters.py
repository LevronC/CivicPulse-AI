from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.contracts.articles import ArticleCreate
from src.services.ingestion.adapters import (
    GdeltConfig,
    GdeltSourceAdapter,
    NewsApiConfig,
    NewsApiSourceAdapter,
    RssSourceAdapter,
)
from src.services.ingestion.normalization import clean_text, parse_gdelt_datetime
from src.services.ingestion.types import NoopRateLimiter


@dataclass
class FakeHttpClient:
    json_payload: dict[str, Any] | None = None
    text_payload: str | None = None

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        assert self.json_payload is not None
        return self.json_payload

    def get_text(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        assert self.text_payload is not None
        return self.text_payload


def test_clean_text_removes_html_and_compacts_whitespace() -> None:
    assert clean_text("<p>Alpha&nbsp; beta</p>\n\nGamma") == "Alpha beta Gamma"


def test_parse_gdelt_datetime_returns_utc_datetime() -> None:
    parsed = parse_gdelt_datetime("20240522T153000Z")
    assert parsed.isoformat() == "2024-05-22T15:30:00+00:00"


def test_newsapi_adapter_normalizes_articles() -> None:
    adapter = NewsApiSourceAdapter(
        config=NewsApiConfig(api_key="test-key", query="test", page_size=1),
        http_client=FakeHttpClient(
            json_payload={
                "articles": [
                    {
                        "url": "https://example.com/news",
                        "title": "Policy vote scheduled",
                        "description": "Lawmakers will vote today.",
                        "publishedAt": "2024-05-22T15:30:00Z",
                    }
                ]
            }
        ),
        rate_limiter=NoopRateLimiter(),
    )

    articles = adapter.fetch()

    assert len(articles) == 1
    assert isinstance(articles[0], ArticleCreate)
    assert articles[0].source == "newsapi"
    assert articles[0].url == "https://example.com/news"


def test_gdelt_adapter_normalizes_articles() -> None:
    adapter = GdeltSourceAdapter(
        config=GdeltConfig(query="test", max_records=1),
        http_client=FakeHttpClient(
            json_payload={
                "articles": [
                    {
                        "url": "https://example.com/gdelt",
                        "title": "Regional protests continue",
                        "seendate": "20240522T153000Z",
                        "language": "English",
                    }
                ]
            }
        ),
        rate_limiter=NoopRateLimiter(),
    )

    articles = adapter.fetch()

    assert len(articles) == 1
    assert articles[0].source == "gdelt"
    assert articles[0].title == "Regional protests continue"


def test_rss_adapter_normalizes_feed_items() -> None:
    adapter = RssSourceAdapter(
        feed_urls=["https://example.com/rss"],
        http_client=FakeHttpClient(
            text_payload="""
            <rss version="2.0">
              <channel>
                <item>
                  <title>Flood response expands</title>
                  <link>https://example.com/rss/flood</link>
                  <description><![CDATA[Emergency crews expanded response.]]></description>
                  <pubDate>Wed, 22 May 2024 15:30:00 GMT</pubDate>
                </item>
              </channel>
            </rss>
            """
        ),
        rate_limiter=NoopRateLimiter(),
    )

    articles = adapter.fetch()

    assert len(articles) == 1
    assert articles[0].source == "rss"
    assert articles[0].body == "Emergency crews expanded response."
