from __future__ import annotations

"""
HTTP boundary for source connectors.

Purpose:
  Isolate requests/session/retry behavior from adapters so provider modules
  focus only on endpoint parameters and payload normalization.

Responsibilities:
  Apply timeout, transient retry, structured logging, and response validation.

Extension points:
  Replace RequestHttpClient with an async client, cached client, or circuit
  breaker wrapper without touching adapters or ingestion orchestration.

Future replacement strategy:
  In worker deployments this class can become an httpx.AsyncClient wrapper while
  preserving the small get_json/get_text interface used by adapters.
"""

import time
from typing import Any, Protocol

import requests

from src.logging import get_logger
from src.services.ingestion.types import RetryPolicy, SourceFetchError

logger = get_logger("ingestion.http")


class HttpClient(Protocol):
    """Small HTTP interface used by source adapters."""

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        ...

    def get_text(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        ...


class RequestHttpClient:
    """Requests-backed HTTP client with bounded retry and timeout behavior."""

    def __init__(
        self,
        retry_policy: RetryPolicy,
        session: requests.Session | None = None,
    ) -> None:
        self._retry_policy = retry_policy
        self._session = session or requests.Session()

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = self._request("GET", url, params=params, headers=headers)
        try:
            payload = response.json()
        except ValueError as exc:
            raise SourceFetchError(f"Invalid JSON response from {url}") from exc
        if not isinstance(payload, dict):
            raise SourceFetchError(f"Expected JSON object from {url}")
        return payload

    def get_text(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        return self._request("GET", url, params=params, headers=headers).text

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None,
        headers: dict[str, str] | None,
    ) -> requests.Response:
        attempts = max(1, self._retry_policy.attempts)
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = self._session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    timeout=self._retry_policy.timeout_seconds,
                )
                if response.status_code >= 500 or response.status_code == 429:
                    raise SourceFetchError(
                        f"Transient HTTP {response.status_code} from {url}"
                    )
                response.raise_for_status()
                return response
            except (requests.RequestException, SourceFetchError) as exc:
                last_error = exc
                logger.warning(
                    "Source HTTP attempt failed",
                    extra={
                        "extra_data": {
                            "url": url,
                            "attempt": attempt,
                            "attempts": attempts,
                            "error": str(exc),
                        }
                    },
                )
                if attempt < attempts:
                    time.sleep(self._retry_policy.backoff_seconds * attempt)

        raise SourceFetchError(f"Failed to fetch {url}: {last_error}") from last_error
