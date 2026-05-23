from __future__ import annotations

import time

from src.services.enrichment.interfaces.stage import EnrichmentStageInterface, StageResult
from src.services.enrichment.models.manager import ModelManager


class EmbeddingStageV2(EnrichmentStageInterface):
    def __init__(self, model_manager: ModelManager) -> None:
        self._manager = model_manager

    @property
    def name(self) -> str:
        return "embedding"

    @property
    def requires_model(self) -> bool:
        return True

    def process(self, text: str) -> StageResult:
        start = time.monotonic()
        backend = self._manager.get("embedding")
        outputs = backend(text)
        elapsed = (time.monotonic() - start) * 1000
        has_embedding = bool(outputs.get("embedding"))
        return StageResult(
            outputs=outputs,
            confidence=1.0 if has_embedding else 0.0,
            model_name="embedding",
            latency_ms=elapsed,
        )
