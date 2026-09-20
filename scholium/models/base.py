"""The model interface every backend implements: chat, embed, rerank.

Every model call returns one of the typed results below or raises, per
CLAUDE.md: "Every model call returns a typed object or raises. Never parse
free text with regex when JSON mode is available."
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel


class Message(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str


class ChatResult(BaseModel):
    text: str
    parsed: dict[str, Any] | list[Any] | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: float
    model_name: str
    backend: str


class EmbedResult(BaseModel):
    vectors: list[list[float]]
    dim: int
    latency_ms: float
    model_name: str
    backend: str


class RerankResult(BaseModel):
    scores: list[float]
    reasons: list[str | None]
    latency_ms: float
    model_name: str
    backend: str


class ModelBackend(Protocol):
    """A backend need not implement every operation. A backend that cannot
    do something (SPECTER2 does not chat) says so by raising NotImplementedError
    rather than being forced to implement a method it has no honest answer for.
    """

    name: str

    def chat(
        self,
        messages: list[Message],
        *,
        model: str,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> ChatResult: ...

    def embed(self, texts: list[str], *, model: str) -> EmbedResult: ...

    def rerank(self, query: str, documents: list[str], *, model: str) -> RerankResult: ...


class ModelError(RuntimeError):
    """Raised on a backend failure. Never silently swallowed; a tool that
    cannot get a model result stops and reports, per rule 2 (retrieval over
    generation: nothing is invented to paper over a failed call).
    """
