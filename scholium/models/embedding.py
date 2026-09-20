"""SPECTER2 paper embeddings via sentence-transformers, cached to disk by text
hash, per plan section 5.2 Day 9 to 11. This backend only embeds; it has no
chat or rerank story, and says so by raising rather than pretending.

sentence-transformers (and its torch dependency) is the `embed` optional
extra, not a core dependency, since it is only needed once Find's embedding
channel or Read's chunk embeddings actually run. The import is lazy so the
rest of the package works without it installed.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from scholium.http import DiskCache
from scholium.models.base import ChatResult, EmbedResult, Message, RerankResult


class Specter2Backend:
    name = "specter2"

    def __init__(self, model_name: str, *, cache_dir: Path) -> None:
        self._model_name = model_name
        self._cache = DiskCache(cache_dir)
        self._model = None  # loaded lazily on first embed() call

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise ImportError(
                "sentence-transformers is not installed. Install the 'embed' "
                "extra: pip install -e '.[embed]'"
            ) from exc
        self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: list[str], *, model: str) -> EmbedResult:
        start = time.monotonic()
        to_compute: list[tuple[int, str]] = []
        vectors: list[list[float] | None] = [None] * len(texts)
        for i, text in enumerate(texts):
            key = self._cache_key(model, text)
            cached = self._cache.get(key)
            if cached is not None:
                vectors[i] = json.loads(cached)
            else:
                to_compute.append((i, text))

        if to_compute:
            encoder = self._load()
            fresh = encoder.encode([t for _, t in to_compute], convert_to_numpy=True)
            for (i, text), vector in zip(to_compute, fresh, strict=True):
                vec_list = [float(v) for v in vector]
                vectors[i] = vec_list
                self._cache.set(self._cache_key(model, text), json.dumps(vec_list).encode("utf-8"))

        latency_ms = (time.monotonic() - start) * 1000
        dim = len(vectors[0]) if vectors else 0
        return EmbedResult(
            vectors=vectors, dim=dim, latency_ms=latency_ms, model_name=model, backend=self.name
        )

    @staticmethod
    def _cache_key(model: str, text: str) -> str:
        return f"embed:{model}:{text}"

    def chat(
        self, messages: list[Message], *, model: str, json_schema=None, temperature: float = 0.0
    ) -> ChatResult:
        raise NotImplementedError("SPECTER2 is an embedding-only backend; it does not chat.")

    def rerank(self, query: str, documents: list[str], *, model: str) -> RerankResult:
        raise NotImplementedError(
            "SPECTER2 is an embedding-only backend; use LLMPointwiseReranker or "
            "compute cosine similarity over embed() output."
        )
