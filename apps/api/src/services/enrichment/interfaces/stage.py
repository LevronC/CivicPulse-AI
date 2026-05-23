from __future__ import annotations

"""
Enrichment stage interface.

All enrichment stages implement this protocol. The interface is
deliberately narrow: a stage receives text and returns a typed
StageResult. Stages never know how models are loaded, where
they run (CPU/GPU/remote), or how they are batched.

This separation enables:
  - CPU/GPU switching without touching stage logic
  - ONNX/quantization migration
  - Remote inference provider swap
  - Batching across articles
  - Independent stage testing with mock models
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class StageResult:
    """
    Output of a single enrichment stage execution.

    Every stage produces a typed result with provenance metadata
    so downstream consumers know which model version produced the
    output and how confident the prediction is.
    """

    outputs: dict[str, Any]
    confidence: float = 1.0
    model_name: str = "heuristic"
    model_version: str = "v1"
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    warnings: list[str] = field(default_factory=list)


class EnrichmentStageInterface(ABC):
    """Protocol for enrichment pipeline stages."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique stage identifier used for telemetry and error tracking."""
        ...

    @abstractmethod
    def process(self, text: str) -> StageResult:
        """
        Execute this enrichment stage on the given text.

        Returns a StageResult with outputs, confidence, and provenance.
        Must not raise for recoverable failures — return a StageResult
        with empty outputs and a warning instead.
        """
        ...

    @property
    def requires_model(self) -> bool:
        """Whether this stage needs a model from the ModelManager."""
        return False
