"""Tests for error primitives — ensure structured error responses."""

from src.errors import (
    ConflictError,
    EnrichmentError,
    NotFoundError,
    RateLimitError,
)


class TestNotFoundError:
    def test_message_format(self) -> None:
        err = NotFoundError("Event", "evt-123")
        assert "evt-123" in str(err)
        assert err.status_code == 404

    def test_response_structure(self) -> None:
        err = NotFoundError("Article", "art-abc")
        resp = err.to_response()
        assert resp["error"]["code"] == "NOT_FOUND"
        assert resp["error"]["detail"]["resource"] == "Article"


class TestRateLimitError:
    def test_includes_limit_info(self) -> None:
        err = RateLimitError("client-1", 60)
        assert err.status_code == 429
        resp = err.to_response()
        assert resp["error"]["detail"]["limit_per_min"] == 60


class TestEnrichmentError:
    def test_includes_stage_context(self) -> None:
        err = EnrichmentError("sentiment", "art-1", cause="provider timeout")
        assert "sentiment" in str(err)
        assert err.status_code == 502
        resp = err.to_response()
        assert resp["error"]["detail"]["stage"] == "sentiment"


class TestConflictError:
    def test_basic(self) -> None:
        err = ConflictError("Duplicate article", detail={"url": "https://x.com"})
        assert err.status_code == 409
