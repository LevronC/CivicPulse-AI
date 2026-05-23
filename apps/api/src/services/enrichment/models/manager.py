from __future__ import annotations

"""
Model lifecycle manager.

Owns loading, caching, device placement, and teardown for all
inference models used by enrichment stages. Stages request models
through this manager by name — they never import model libraries
or manage GPU memory directly.

Design constraints:
  - Lazy loading: models are loaded on first request, not at startup
  - Shared instances: same model is reused across stages and batches
  - Device-agnostic: stages receive a callable, not a raw model object
  - Replaceable: swap to ONNX, quantized, or remote inference by
    changing only this module and the model wrapper, not stages

For local development, ModelManager returns heuristic wrappers.
When HuggingFace model names are configured, it loads them on demand.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

from src.logging import get_logger

logger = get_logger("enrichment.models")


class ModelBackend(Protocol):
    """
    Inference callable that model wrappers must implement.

    Stages call the backend with text and receive structured output.
    The protocol hides whether inference is local, batched, or remote.
    """

    def __call__(self, text: str) -> dict[str, Any]:
        ...


@dataclass
class ModelSpec:
    """
    Model registration specification.

    Declares how to load a model and what resource constraints it has.
    The factory is only called when the model is first requested.
    """

    name: str
    factory: Callable[[], ModelBackend]
    device: str = "cpu"
    max_memory_mb: int = 0
    loaded: bool = field(default=False, init=False)
    instance: Optional[ModelBackend] = field(default=None, init=False)
    load_time_ms: float = field(default=0.0, init=False)


class ModelManager:
    """
    Thread-safe model registry with lazy loading.

    Usage by stages:
        manager = get_model_manager()
        backend = manager.get("sentiment")
        result = backend(text)
    """

    def __init__(self) -> None:
        self._specs: dict[str, ModelSpec] = {}
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        factory: Callable[[], ModelBackend],
        *,
        device: str = "cpu",
        max_memory_mb: int = 0,
    ) -> None:
        """Register a model factory. Loading is deferred until first get() call."""
        self._specs[name] = ModelSpec(
            name=name,
            factory=factory,
            device=device,
            max_memory_mb=max_memory_mb,
        )

    def get(self, name: str) -> ModelBackend:
        """
        Get a model backend by name. Loads on first access.

        Thread-safe: concurrent get() calls for the same model
        will block until loading completes rather than loading twice.
        """
        spec = self._specs.get(name)
        if spec is None:
            raise KeyError(f"Model '{name}' not registered. Available: {list(self._specs.keys())}")

        if spec.loaded and spec.instance is not None:
            return spec.instance

        with self._lock:
            if spec.loaded and spec.instance is not None:
                return spec.instance

            start = time.monotonic()
            logger.info("Loading model", extra={"model": name, "device": spec.device})
            spec.instance = spec.factory()
            spec.load_time_ms = (time.monotonic() - start) * 1000
            spec.loaded = True
            logger.info(
                "Model loaded",
                extra={"model": name, "load_time_ms": round(spec.load_time_ms, 1)},
            )
            return spec.instance

    def is_loaded(self, name: str) -> bool:
        spec = self._specs.get(name)
        return spec is not None and spec.loaded

    def unload(self, name: str) -> None:
        """Release a model's memory. Next get() will reload it."""
        spec = self._specs.get(name)
        if spec is not None:
            spec.instance = None
            spec.loaded = False
            logger.info("Model unloaded", extra={"model": name})

    def unload_all(self) -> None:
        for name in list(self._specs.keys()):
            self.unload(name)

    def status(self) -> list[dict[str, Any]]:
        """Return loading status for all registered models."""
        return [
            {
                "name": spec.name,
                "loaded": spec.loaded,
                "device": spec.device,
                "load_time_ms": round(spec.load_time_ms, 1),
            }
            for spec in self._specs.values()
        ]


_manager: ModelManager | None = None


def get_model_manager() -> ModelManager:
    global _manager
    if _manager is None:
        _manager = ModelManager()
        _register_defaults(_manager)
    return _manager


def _register_defaults(manager: ModelManager) -> None:
    """
    Register model backends based on deployment configuration.

    Heuristic backends are used by default for stages where no
    transformer model is configured. The embedding stage uses
    sentence-transformers when available (which is always in
    production) to produce semantically meaningful vectors.
    """
    from src.config import get_settings
    from src.services.enrichment.models.heuristic import (
        heuristic_embedding_backend,
        heuristic_entity_backend,
        heuristic_sentiment_backend,
        heuristic_summarization_backend,
        heuristic_topic_backend,
    )

    settings = get_settings()

    manager.register("summarization", lambda: heuristic_summarization_backend)
    manager.register("topic_classification", lambda: heuristic_topic_backend)
    manager.register("sentiment", lambda: heuristic_sentiment_backend)
    manager.register("entity_extraction", lambda: heuristic_entity_backend)

    embedding_model = settings.nlp.embedding_model
    if embedding_model != "heuristic":
        from src.services.enrichment.models.transformers import (
            SentenceTransformerEmbeddingBackend,
        )
        manager.register(
            "embedding",
            lambda: SentenceTransformerEmbeddingBackend(embedding_model),
            max_memory_mb=256,
        )
    else:
        manager.register("embedding", lambda: heuristic_embedding_backend)
