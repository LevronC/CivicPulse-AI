"""
CivicPulse API application factory.

This module is intentionally thin — it wires middleware, registers
route modules, and initializes infrastructure. All business logic
lives in src/services/*, all persistence in src/repositories/*,
and all request handling in src/routes/*.
"""

from contextlib import asynccontextmanager

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.errors.base import CivicPulseError
from src.logging import get_logger, setup_logging
from src.middleware import CorrelationMiddleware
from src.repositories.database import init_db
from src.routes import (
    enrich_router,
    events_router,
    health_router,
    ingest_router,
    intelligence_router,
    stream_router,
    tasks_router,
)

load_dotenv(find_dotenv(usecwd=True))


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(level=settings.log_level, environment=settings.environment)
    init_db()
    yield


app = FastAPI(
    title="CivicPulse API",
    version="0.4.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationMiddleware)


@app.exception_handler(CivicPulseError)
async def civicpulse_error_handler(_request: Request, exc: CivicPulseError) -> JSONResponse:
    logger = get_logger("error_handler")
    logger.warning(
        "Domain error: %s",
        str(exc),
        extra={"code": exc.code, "status": exc.status_code},
    )
    return JSONResponse(status_code=exc.status_code, content=exc.to_response())


app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(enrich_router)
app.include_router(tasks_router)
app.include_router(stream_router)
app.include_router(intelligence_router)
app.include_router(events_router)
