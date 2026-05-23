from __future__ import annotations

"""
In-memory sliding-window rate limiter.

Suitable for single-instance deployments. For multi-instance production
deployments, this should be replaced with a Redis-backed implementation
using the same interface (RateLimiter.check).
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from src.config import get_settings
from src.errors import RateLimitError


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, list[datetime]] = defaultdict(list)

    def check(self, client_key: str) -> None:
        """
        Raises RateLimitError if the client has exceeded the
        configured requests-per-minute threshold.
        """
        limit = get_settings().api.rate_limit_per_min
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=1)

        recent = [t for t in self._buckets[client_key] if t > window_start]
        if len(recent) >= limit:
            raise RateLimitError(client=client_key, limit=limit)

        recent.append(now)
        self._buckets[client_key] = recent
