from __future__ import annotations

import time

from src.services.enrichment.interfaces.stage import EnrichmentStageInterface, StageResult
from src.services.enrichment.models.manager import ModelManager


class EntityStageV2(EnrichmentStageInterface):
    def __init__(self, model_manager: ModelManager) -> None:
        self._manager = model_manager

    @property
    def name(self) -> str:
        return "entity_extraction"

    @property
    def requires_model(self) -> bool:
        return True

    def process(self, text: str) -> StageResult:
        start = time.monotonic()
        backend = self._manager.get("entity_extraction")
        outputs = backend(text)
        elapsed = (time.monotonic() - start) * 1000
        entity_count = len(outputs.get("entities", []))
        return StageResult(
            outputs=outputs,
            confidence=min(entity_count / 5.0, 1.0) if entity_count else 0.0,
            model_name="entity_extraction",
            latency_ms=elapsed,
        )
