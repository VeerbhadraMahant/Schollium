"""Stub backend for tests. Model calls in tests use this rather than a real
model, per plan section 3.3. Chat responses come from a fixture dict (or a
JSON file loaded via `from_fixture_file`); embed and rerank are deterministic
functions of the input text, so the same input always produces the same
output without needing a fixture entry for every case.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scholium.models.base import ChatResult, EmbedResult, Message, ModelError, RerankResult

DEFAULT_EMBED_DIM = 8


def _deterministic_vector(text: str, dim: int) -> list[float]:
    """A stable, cheap stand-in for a real embedding: near-identical texts do
    not necessarily land near each other, but the same text always produces
    the same vector, which is what tests actually need.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    while len(digest) < dim * 4:
        digest += hashlib.sha256(digest).digest()
    raw = struct.unpack(f"{dim}i", digest[: dim * 4])
    return [v / 2_147_483_648.0 for v in raw]


class StubBackend:
    name = "stub"

    def __init__(
        self,
        chat_fixtures: dict[str, dict[str, Any]] | None = None,
        *,
        embed_dim: int = DEFAULT_EMBED_DIM,
    ) -> None:
        self._chat_fixtures = chat_fixtures or {}
        self._embed_dim = embed_dim

    @classmethod
    def from_fixture_file(cls, path: Path) -> StubBackend:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            chat_fixtures=data.get("chat", {}), embed_dim=data.get("embed_dim", DEFAULT_EMBED_DIM)
        )

    def chat(
        self,
        messages: list[Message],
        *,
        model: str,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> ChatResult:
        key = messages[-1].content if messages else ""
        fixture = self._chat_fixtures.get(key, self._chat_fixtures.get("default"))
        if fixture is None:
            raise ModelError(
                f"stub backend has no chat fixture for key {key!r} and no 'default' fixture"
            )
        text = fixture.get("text", "")
        parsed = fixture.get("parsed")
        if json_schema is not None and parsed is None:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ModelError(f"stub fixture text is not valid JSON: {exc}") from exc
        return ChatResult(
            text=text, parsed=parsed, latency_ms=0.0, model_name=model, backend=self.name
        )

    def embed(self, texts: list[str], *, model: str) -> EmbedResult:
        vectors = [_deterministic_vector(t, self._embed_dim) for t in texts]
        return EmbedResult(
            vectors=vectors,
            dim=self._embed_dim,
            latency_ms=0.0,
            model_name=model,
            backend=self.name,
        )

    def rerank(self, query: str, documents: list[str], *, model: str) -> RerankResult:
        query_terms = set(query.lower().split())
        scores: list[float] = []
        reasons: list[str | None] = []
        for doc in documents:
            overlap = query_terms & set(doc.lower().split())
            scores.append(float(len(overlap)))
            reasons.append(
                f"{len(overlap)} overlapping term(s) with the query" if overlap else "no overlap"
            )
        return RerankResult(
            scores=scores, reasons=reasons, latency_ms=0.0, model_name=model, backend=self.name
        )
