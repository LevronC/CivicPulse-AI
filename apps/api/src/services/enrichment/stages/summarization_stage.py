from __future__ import annotations

import time
from datetime import datetime, timezone

from src.services.enrichment.interfaces.stage import EnrichmentStageInterface, StageResult
from src.services.enrichment.models.manager import ModelManager


class SummarizationStageV2(EnrichmentStageInterface):
    """
    Summarization stage that delegates to whatever backend the
    ModelManager provides — heuristic, transformer, or remote API.
    """

    def __init__(self, model_manager: ModelManager) -> None:
        self._manager = model_manager

    @property
    def name(self) -> str:
        return "summarization"

    @property
    def requires_model(self) -> bool:
        return True

    def process(self, text: str) -> StageResult:
        start = time.monotonic()
        backend = self._manager.get("summarization")
        outputs = backend(text)
        elapsed = (time.monotonic() - start) * 1000
        return StageResult(
            outputs=outputs,
            confidence=1.0 if outputs.get("summary") else 0.0,
            model_name="summarization",
            latency_ms=elapsed,
        )
