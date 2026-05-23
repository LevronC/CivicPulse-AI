from __future__ import annotations

"""
Transformer-backed model backends.

Each backend wraps a HuggingFace model behind the ModelBackend
callable interface. Stages never import this module directly —
they receive the backend from ModelManager.get().

The SentenceTransformerEmbeddingBackend produces 384-dim embeddings
using all-MiniLM-L6-v2. These embeddings have genuine semantic
similarity properties, enabling the clustering engine to separate
"Ukraine conflict" from "Ebola outbreak" from "China mine disaster"
based on meaning rather than character frequency overlap.
"""

from typing import Any

from src.logging import get_logger

logger = get_logger("enrichment.models.transformers")


class SentenceTransformerEmbeddingBackend:
    """
    Embedding backend backed by sentence-transformers.

    Lazy-initializes the model on first call (which is itself
    triggered lazily by ModelManager on first stage.process()).
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer

        logger.info("Loading sentence-transformer", extra={"model": self._model_name})
        self._model = SentenceTransformer(self._model_name)
        logger.info(
            "Sentence-transformer loaded",
            extra={"model": self._model_name, "dims": self._model.get_sentence_embedding_dimension()},
        )

    def __call__(self, text: str) -> dict[str, Any]:
        self._ensure_loaded()
        embedding = self._model.encode(text, normalize_embeddings=True)
        return {"embedding": embedding.tolist()}
