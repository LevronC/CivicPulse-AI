from src.services.ingestion.dedupe import generate_article_id
from src.services.ingestion.registry import build_source_adapters
from src.services.ingestion.ingest_service import IngestionService
from src.services.ingestion.source_adapter import MockSourceAdapter, SourceAdapter

__all__ = [
    "build_source_adapters",
    "IngestionService",
    "MockSourceAdapter",
    "SourceAdapter",
    "generate_article_id",
]
