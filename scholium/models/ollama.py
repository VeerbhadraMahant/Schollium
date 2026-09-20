"""Ollama backend: local by default, per plan section 2.3. Uses Ollama's HTTP
API directly rather than a client library, since the API surface needed here
(chat with JSON mode, embeddings) is small.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from scholium.models._retry import http_retry
from scholium.models.base import ChatResult, EmbedResult, Message, ModelError, RerankResult


class OllamaBackend:
    name = "ollama"

    def __init__(self, base_url: str, *, timeout: float = 60.0, max_retries: int = 4) -> None:
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout)
        self._max_retries = max_retries

    def close(self) -> None:
        self._client.close()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        @http_retry(self._max_retries)
        def _do() -> httpx.Response:
            response = self._client.post(path, json=payload)
            response.raise_for_status()
            return response

        try:
            return _do().json()
        except httpx.HTTPError as exc:
            raise ModelError(f"ollama request to {path} failed: {exc}") from exc

    def chat(
        self,
        messages: list[Message],
        *,
        model: str,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> ChatResult:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_schema is not None:
            payload["format"] = "json"

        start = time.monotonic()
        data = self._post("/api/chat", payload)
        latency_ms = (time.monotonic() - start) * 1000

        text = data.get("message", {}).get("content", "")
        parsed = None
        if json_schema is not None:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ModelError(f"ollama chat did not return valid JSON: {exc}") from exc

        return ChatResult(
            text=text,
            parsed=parsed,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            latency_ms=latency_ms,
            model_name=model,
            backend=self.name,
        )

    def embed(self, texts: list[str], *, model: str) -> EmbedResult:
        start = time.monotonic()
        vectors = [
            self._post("/api/embeddings", {"model": model, "prompt": t})["embedding"] for t in texts
        ]
        latency_ms = (time.monotonic() - start) * 1000
        dim = len(vectors[0]) if vectors else 0
        return EmbedResult(
            vectors=vectors, dim=dim, latency_ms=latency_ms, model_name=model, backend=self.name
        )

    def rerank(self, query: str, documents: list[str], *, model: str) -> RerankResult:
        raise NotImplementedError(
            "Ollama has no native rerank endpoint. Use "
            "scholium.models.rerank.LLMPointwiseReranker, which drives this "
            "backend's chat() one document at a time."
        )
