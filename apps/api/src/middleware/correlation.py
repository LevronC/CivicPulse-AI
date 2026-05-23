"""
Correlation ID middleware.

Assigns a unique correlation ID to every inbound request and propagates
it via contextvars so that all log entries within the request lifecycle
share the same ID. If the caller supplies X-Correlation-ID, it is reused
(useful for tracing across service boundaries).
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.logging.logger import correlation_id_var


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming_id = request.headers.get("x-correlation-id")
        cid = incoming_id or str(uuid.uuid4())
        correlation_id_var.set(cid)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response
