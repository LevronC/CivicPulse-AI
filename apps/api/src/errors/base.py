"""
Domain error hierarchy.

Every error carries structured context (error code, detail, optional metadata)
so that API handlers can produce consistent error responses and structured
logs can capture diagnostic data without string parsing.

The hierarchy is shallow by design — add new leaf errors as subsystems grow,
but resist deep inheritance chains.
"""

from typing import Any, Dict, Optional


class CivicPulseError(Exception):
    """Base error for all domain exceptions."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.detail = detail or {}

    def to_response(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": str(self),
                "detail": self.detail,
            }
        }


class NotFoundError(CivicPulseError):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            f"{resource} not found: {identifier}",
            code="NOT_FOUND",
            status_code=404,
            detail={"resource": resource, "id": identifier},
        )


class ConflictError(CivicPulseError):
    def __init__(self, message: str, *, detail: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message,
            code="CONFLICT",
            status_code=409,
            detail=detail,
        )


class ValidationError(CivicPulseError):
    def __init__(self, message: str, *, detail: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            status_code=422,
            detail=detail,
        )


class RateLimitError(CivicPulseError):
    def __init__(self, client: str, limit: int) -> None:
        super().__init__(
            f"Rate limit exceeded for {client}: {limit}/min",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            detail={"client": client, "limit_per_min": limit},
        )


class IngestionError(CivicPulseError):
    """Raised when article ingestion fails (source fetch, normalization, persistence)."""

    def __init__(self, message: str, *, detail: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message,
            code="INGESTION_ERROR",
            status_code=502,
            detail=detail,
        )


class EnrichmentError(CivicPulseError):
    """
    Raised when an enrichment stage fails.

    Enrichment errors are recoverable — the pipeline should record
    the failure and continue with partial enrichment rather than
    discarding the entire article.
    """

    def __init__(
        self,
        stage: str,
        article_id: str,
        *,
        cause: str = "",
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            f"Enrichment failed at stage '{stage}' for article {article_id}: {cause}",
            code="ENRICHMENT_ERROR",
            status_code=502,
            detail={"stage": stage, "article_id": article_id, **(detail or {})},
        )
