from __future__ import annotations

"""
RSS/Atom source adapter.

Purpose:
  Fetch configured RSS or Atom feeds and normalize feed entries to ArticleCreate.

Responsibilities:
  Parse XML formats, handle per-feed failures, and preserve the generic
  SourceAdapter interface used by ingestion orchestration.

Extension points:
  Add feed-specific extraction rules through small helper functions, not by
  changing IngestionService or route handlers.

Future replacement strategy:
  Replace ElementTree parsing with feedparser or a managed feed service while
  keeping fetch() output and source metadata unchanged.
"""

from xml.etree import ElementTree

from src.contracts.articles import ArticleCreate
from src.logging import get_logger
from src.services.ingestion.http_client import HttpClient
from src.services.ingestion.normalization import (
    build_article,
    clean_text,
    parse_provider_datetime,
)
from src.services.ingestion.source_adapter import SourceAdapter
from src.services.ingestion.types import (
    RateLimitContext,
    RateLimiter,
    SourceMetadata,
    SourceNormalizationError,
)

logger = get_logger("ingestion.rss")


class RssSourceAdapter(SourceAdapter):
    """Adapter for RSS 2.0 and Atom feeds."""

    def __init__(
        self,
        *,
        feed_urls: list[str],
        http_client: HttpClient,
        rate_limiter: RateLimiter,
    ) -> None:
        self._feed_urls = feed_urls
        self._http_client = http_client
        self._rate_limiter = rate_limiter

    @property
    def source_name(self) -> str:
        return "rss"

    @property
    def metadata(self) -> SourceMetadata:
        return SourceMetadata(provider="rss", display_name="RSS Feeds")

    def fetch(self) -> list[ArticleCreate]:
        articles: list[ArticleCreate] = []
        for feed_url in self._feed_urls:
            self._rate_limiter.wait(
                RateLimitContext(provider=self.source_name, operation="fetch_feed")
            )
            try:
                xml_text = self._http_client.get_text(feed_url)
                articles.extend(self._parse_feed(xml_text, feed_url))
            except Exception:
                logger.exception("RSS feed fetch failed", extra={"feed_url": feed_url})
        return articles

    def _parse_feed(self, xml_text: str, feed_url: str) -> list[ArticleCreate]:
        root = ElementTree.fromstring(xml_text)
        if _strip_namespace(root.tag) == "rss":
            return self._parse_rss_items(root, feed_url)
        return self._parse_atom_entries(root, feed_url)

    def _parse_rss_items(
        self, root: ElementTree.Element, feed_url: str
    ) -> list[ArticleCreate]:
        items = root.findall("./channel/item")
        parsed: list[ArticleCreate] = []
        for item in items:
            try:
                title = _child_text(item, "title")
                link = _child_text(item, "link")
                body = _child_text(item, "description") or title
                published = _child_text(item, "pubDate")
                parsed.append(
                    build_article(
                        source=self.source_name,
                        url=link,
                        title=title,
                        body=body,
                        published_at=parse_provider_datetime(published),
                    )
                )
            except SourceNormalizationError as exc:
                logger.warning(
                    "RSS item skipped",
                    extra={"extra_data": {"feed_url": feed_url, "error": str(exc)}},
                )
        return parsed

    def _parse_atom_entries(
        self, root: ElementTree.Element, feed_url: str
    ) -> list[ArticleCreate]:
        parsed: list[ArticleCreate] = []
        for entry in root.findall(".//{*}entry"):
            try:
                title = _child_text(entry, "title")
                link = _atom_link(entry)
                body = _child_text(entry, "summary") or _child_text(entry, "content") or title
                published = _child_text(entry, "published") or _child_text(entry, "updated")
                parsed.append(
                    build_article(
                        source=self.source_name,
                        url=link,
                        title=title,
                        body=body,
                        published_at=parse_provider_datetime(published),
                    )
                )
            except SourceNormalizationError as exc:
                logger.warning(
                    "Atom entry skipped",
                    extra={"extra_data": {"feed_url": feed_url, "error": str(exc)}},
                )
        return parsed


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(parent: ElementTree.Element, name: str) -> str:
    child = parent.find(name)
    if child is None:
        child = parent.find(f"{{*}}{name}")
    return clean_text(child.text if child is not None else "")


def _atom_link(entry: ElementTree.Element) -> str:
    for link in entry.findall("{*}link"):
        if link.attrib.get("rel", "alternate") == "alternate" and link.attrib.get("href"):
            return clean_text(link.attrib["href"])
    return ""
