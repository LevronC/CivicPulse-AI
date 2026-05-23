from src.routes.health import router as health_router
from src.routes.ingest import router as ingest_router
from src.routes.enrich import router as enrich_router
from src.routes.events import router as events_router
from src.routes.intelligence import router as intelligence_router
from src.routes.stream import router as stream_router
from src.routes.tasks import router as tasks_router

__all__ = [
    "enrich_router",
    "events_router",
    "health_router",
    "ingest_router",
    "intelligence_router",
    "stream_router",
    "tasks_router",
]
