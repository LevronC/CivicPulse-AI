from __future__ import annotations

import time

from src.services.enrichment.interfaces.stage import EnrichmentStageInterface, StageResult
from src.services.enrichment.models.manager import ModelManager


class TopicStageV2(EnrichmentStageInterface):
    def __init__(self, model_manager: ModelManager) -> None:
        self._manager = model_manager

    @property
    def name(self) -> str:
        return "topic_classification"

    @property
    def requires_model(self) -> bool:
        return True

    def process(self, text: str) -> StageResult:
        start = time.monotonic()
        backend = self._manager.get("topic_classification")
        outputs = backend(text)
        elapsed = (time.monotonic() - start) * 1000
        return StageResult(
            outputs=outputs,
            confidence=0.8 if outputs.get("topic") else 0.0,
            model_name="topic_classification",
            latency_ms=elapsed,
        )
