from __future__ import annotations

"""
Article repository — persistence boundary for articles and enrichments.

All database operations for articles are isolated here. The API layer
and domain services never construct SQL directly; they call repository
methods that return domain contracts (Pydantic models).

Idempotency: insert_article uses ON CONFLICT DO NOTHING to safely
handle replay/retry storms from ingestion workers without raising errors.
"""

from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.contracts.articles import ArticleEnriched, ArticleRecord, EnrichmentResult
from src.contracts.enums import SentimentLabel, Topic
from src.logging import get_logger
from src.repositories.db_models import ArticleRow, EnrichmentRow

logger = get_logger("repo.article")


class ArticleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert_article(self, article_id: str, data: dict) -> bool:
        """
        Insert an article idempotently.

        Returns True if a new row was inserted, False if the article
        already existed (deduplicated). Uses PostgreSQL's ON CONFLICT
        to avoid race conditions under concurrent ingestion.
        """
        stmt = (
            pg_insert(ArticleRow)
            .values(
                id=article_id,
                source=data["source"],
                url=data["url"],
                title=data["title"],
                body=data["body"],
                published_at=data["published_at"],
                language=data.get("language", "en"),
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
        result = self._session.execute(stmt)
        inserted = (result.rowcount or 0) > 0
        if inserted:
            logger.info("Article inserted", extra={"article_id": article_id})
        return inserted

    def exists(self, article_id: str) -> bool:
        stmt = select(ArticleRow.id).where(ArticleRow.id == article_id)
        return self._session.execute(stmt).scalar_one_or_none() is not None

    def get_unenriched_ids(self, limit: int = 100) -> list[str]:
        """Return article IDs that have no enrichment record yet."""
        stmt = (
            select(ArticleRow.id)
            .outerjoin(EnrichmentRow, ArticleRow.id == EnrichmentRow.article_id)
            .where(EnrichmentRow.article_id.is_(None))
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())

    def get_article(self, article_id: str) -> ArticleRecord | None:
        row = self._session.get(ArticleRow, article_id)
        if row is None:
            return None
        return ArticleRecord(
            id=row.id,
            source=row.source,
            url=row.url,
            title=row.title,
            body=row.body,
            published_at=row.published_at,
            language=row.language,
            inserted_at=row.inserted_at,
        )

    def save_enrichment(self, article_id: str, result: EnrichmentResult) -> None:
        """
        Persist enrichment results with upsert semantics.

        If enrichment is re-run (e.g., after model upgrade), the new
        results overwrite the previous ones rather than creating duplicates.
        """
        stmt = (
            pg_insert(EnrichmentRow)
            .values(
                article_id=article_id,
                summary=result.summary or "",
                topic=(result.topic or Topic.OTHER).value,
                sentiment=(result.sentiment or SentimentLabel.NEUTRAL).value,
                entities=result.entities,
                embedding=result.embedding,
                model_version=result.enrichment_version,
                enriched_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_update(
                index_elements=["article_id"],
                set_={
                    "summary": result.summary or "",
                    "topic": (result.topic or Topic.OTHER).value,
                    "sentiment": (result.sentiment or SentimentLabel.NEUTRAL).value,
                    "entities": result.entities,
                    "embedding": result.embedding,
                    "model_version": result.enrichment_version,
                    "enriched_at": datetime.now(timezone.utc),
                },
            )
        )
        self._session.execute(stmt)
        logger.info("Enrichment saved", extra={"article_id": article_id})

    def get_all_enriched(self) -> list[ArticleEnriched]:
        """
        Load all enriched articles for clustering.

        For production scale this should use cursor-based pagination,
        but for the initial release with bounded dataset sizes,
        full-table load is acceptable during rebuild operations.
        """
        stmt = select(ArticleRow, EnrichmentRow).join(
            EnrichmentRow, ArticleRow.id == EnrichmentRow.article_id
        )
        rows = self._session.execute(stmt).all()
        return [
            ArticleEnriched(
                id=a.id,
                source=a.source,
                url=a.url,
                title=a.title,
                body=a.body,
                published_at=a.published_at,
                language=a.language,
                inserted_at=a.inserted_at,
                summary=e.summary,
                topic=Topic(e.topic),
                sentiment=SentimentLabel(e.sentiment),
                entities=e.entities,
                embedding=e.embedding,
                enriched_at=e.enriched_at,
            )
            for a, e in rows
        ]

    def count(self) -> int:
        stmt = select(text("count(*)")).select_from(ArticleRow)
        return self._session.execute(stmt).scalar_one()

    def enriched_count(self) -> int:
        stmt = select(text("count(*)")).select_from(EnrichmentRow)
        return self._session.execute(stmt).scalar_one()
