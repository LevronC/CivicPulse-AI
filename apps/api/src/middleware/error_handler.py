"""
Global error handler middleware.

Converts domain errors (CivicPulseError hierarchy) into structured
JSON responses with appropriate HTTP status codes. Unhandled exceptions
produce a generic 500 response with a correlation ID for debugging.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from src.errors.base import CivicPulseError
from src.logging import get_logger
from src.logging.logger import correlation_id_var

logger = get_logger("error_handler")


async def error_handler_middleware(request: Request, call_next):  # noqa: ANN001
    try:
        return await call_next(request)
    except CivicPulseError as exc:
        logger.warning(
            "Domain error: %s",
            str(exc),
            extra={"code": exc.code, "status": exc.status_code},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_response(),
        )
    except Exception:
        cid = correlation_id_var.get()
        logger.exception("Unhandled exception (correlation_id=%s)", cid)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "correlation_id": cid,
                }
            },
        )
