"""Any OpenAI-compatible HTTP endpoint: OpenAI, Anthropic via a proxy, Gemini,
vLLM, LM Studio. Same interface as the Ollama backend so a step can switch
between them by changing config alone.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from scholium.models._retry import http_retry
from scholium.models.base import ChatResult, EmbedResult, Message, ModelError, RerankResult


class OpenAICompatibleBackend:
    name = "openai_compatible"

    def __init__(
        self, base_url: str, *, api_key: str = "", timeout: float = 60.0, max_retries: int = 4
    ) -> None:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout, headers=headers)
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
            raise ModelError(f"openai-compatible request to {path} failed: {exc}") from exc

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
            "temperature": temperature,
        }
        if json_schema is not None:
            payload["response_format"] = {"type": "json_object"}

        start = time.monotonic()
        data = self._post("/chat/completions", payload)
        latency_ms = (time.monotonic() - start) * 1000

        choice = data["choices"][0]["message"]
        text = choice.get("content", "") or ""
        usage = data.get("usage", {})
        parsed = None
        if json_schema is not None:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ModelError(f"model did not return valid JSON: {exc}") from exc

        return ChatResult(
            text=text,
            parsed=parsed,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            latency_ms=latency_ms,
            model_name=model,
            backend=self.name,
        )

    def embed(self, texts: list[str], *, model: str) -> EmbedResult:
        start = time.monotonic()
        data = self._post("/embeddings", {"model": model, "input": texts})
        latency_ms = (time.monotonic() - start) * 1000
        vectors = [item["embedding"] for item in data["data"]]
        dim = len(vectors[0]) if vectors else 0
        return EmbedResult(
            vectors=vectors, dim=dim, latency_ms=latency_ms, model_name=model, backend=self.name
        )

    def rerank(self, query: str, documents: list[str], *, model: str) -> RerankResult:
        raise NotImplementedError(
            "No standard OpenAI-compatible rerank endpoint. Use "
            "scholium.models.rerank.LLMPointwiseReranker."
        )
