from __future__ import annotations

"""
Shared ingestion connector types.

Purpose:
  Keep provider configuration, metadata, retry, and rate-limit contracts
  independent from concrete adapters.

Responsibilities:
  Define small data structures that adapters can depend on without importing
  service orchestration or route code.

Extension points:
  Add provider-specific config objects in this module only when the shape is
  shared across adapters. Keep provider payload parsing inside adapter modules.

Future replacement strategy:
  These contracts can move into a worker package or shared SDK without changing
  adapter behavior because they do not depend on FastAPI or SQLAlchemy.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol


@dataclass(frozen=True)
class RetryPolicy:
    """Network retry policy for transient source/provider failures."""

    attempts: int = 3
    backoff_seconds: float = 0.25
    timeout_seconds: float = 10.0


@dataclass(frozen=True)
class SourceMetadata:
    """Provider metadata emitted by adapters for logs, metrics, and audits."""

    provider: str
    display_name: str
    homepage_url: Optional[str] = None
    configured_at: Optional[datetime] = None


@dataclass(frozen=True)
class RateLimitContext:
    """Minimal context passed to rate-limit hooks before a provider call."""

    provider: str
    operation: str


class RateLimiter(Protocol):
    """
    Hook for provider-specific rate limiting.

    Implementations may block, sleep, raise, or simply record metrics. The
    default implementation is intentionally no-op so adapters stay testable and
    deployments can swap in Redis/token-bucket logic later.
    """

    def wait(self, context: RateLimitContext) -> None:
        ...


class NoopRateLimiter:
    """Default rate limiter used when no deployment-specific limiter is wired."""

    def wait(self, context: RateLimitContext) -> None:
        return None


class SourceFetchError(RuntimeError):
    """Raised when a source cannot be fetched after retry policy is exhausted."""


class SourceNormalizationError(ValueError):
    """Raised when provider payloads cannot be converted into ArticleCreate."""
