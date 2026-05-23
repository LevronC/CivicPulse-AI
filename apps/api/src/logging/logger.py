from __future__ import annotations

"""
Structured logging with JSON output and correlation ID propagation.

All log entries include:
  - timestamp (ISO 8601)
  - level
  - module
  - correlation_id (propagated from request context)
  - environment

This provides grep-friendly, machine-parseable logs that
integrate with log aggregation systems (ELK, Datadog, etc.)
without requiring custom parsing rules.
"""

import logging
import sys
from contextvars import ContextVar
from typing import Any

import json

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="none")


class StructuredFormatter(logging.Formatter):
    """Emits JSON log lines with correlation context."""

    def __init__(self, environment: str = "development") -> None:
        super().__init__()
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
            "environment": self.environment,
        }
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = str(record.exc_info[1])
            entry["exception_type"] = type(record.exc_info[1]).__name__
        if hasattr(record, "extra_data"):
            entry["data"] = record.extra_data
        return json.dumps(entry, default=str)


def setup_logging(level: str = "INFO", environment: str = "development") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter(environment=environment))

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"civicpulse.{name}")
