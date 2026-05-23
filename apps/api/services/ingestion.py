import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from models import ArticleIn


def article_id(url: str, title: str) -> str:
    return hashlib.sha256(f"{url}:{title}".encode("utf-8")).hexdigest()[:16]


def dedupe_articles(incoming: list[ArticleIn], existing_ids: set[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for article in incoming:
        aid = article_id(article.url, article.title)
        if aid in existing_ids:
            continue
        out.append({"id": aid, **article.model_dump()})
        existing_ids.add(aid)
    return out


def mock_news_batch() -> list[ArticleIn]:
    now = datetime.now(timezone.utc)
    return [
        ArticleIn(
            source="newsapi",
            url="https://example.com/politics-tax-protest",
            title="Demonstrations rise over new tax policy",
            body="Thousands gathered near parliament as lawmakers introduced a new tax bill.",
            published_at=now - timedelta(minutes=5),
        ),
        ArticleIn(
            source="gdelt",
            url="https://example.com/earthquake-update",
            title="Regional authorities respond to moderate earthquake",
            body="Emergency teams were dispatched after a 5.8 quake hit coastal communities.",
            published_at=now - timedelta(minutes=11),
        ),
    ]
