"""The default reranker: LLM pointwise scoring, per plan section 5.2 Day 9 to
11. Wraps any chat-capable backend rather than being its own backend, so it
works with Ollama, an OpenAI-compatible endpoint or the stub without
duplicating logic per backend. A cross-encoder backend can slot in later
alongside this one; this module does not have to change when it does.
"""

from __future__ import annotations

from pathlib import Path

from scholium.models.base import ChatResult, Message, ModelBackend, ModelError, RerankResult
from scholium.prompts import load_prompt

PROMPT_NAME = "rerank.pointwise"
PROMPT_VERSION = 1
JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 1, "maximum": 5},
        "reason": {"type": "string"},
    },
    "required": ["score", "reason"],
}


class LLMPointwiseReranker:
    """Scores each document one at a time, asking for a 1 to 5 relevance score
    and a one-sentence reason, matching plan section 6.3 step 7.
    """

    def __init__(self, backend: ModelBackend, *, prompts_dir: Path) -> None:
        self._backend = backend
        self._template = load_prompt(PROMPT_NAME, PROMPT_VERSION, prompts_dir=prompts_dir)

    def rerank(self, query: str, documents: list[str], *, model: str) -> RerankResult:
        scores: list[float] = []
        reasons: list[str | None] = []
        total_latency = 0.0
        for document in documents:
            prompt = self._template.format(query=query, document=document)
            result: ChatResult = self._backend.chat(
                [Message(role="user", content=prompt)],
                model=model,
                json_schema=JSON_SCHEMA,
                temperature=0.0,
            )
            total_latency += result.latency_ms
            if result.parsed is None or "score" not in result.parsed:
                raise ModelError(f"reranker response missing 'score': {result.text!r}")
            scores.append(float(result.parsed["score"]))
            reasons.append(result.parsed.get("reason"))
        return RerankResult(
            scores=scores,
            reasons=reasons,
            latency_ms=total_latency,
            model_name=model,
            backend=f"{self._backend.name}+{PROMPT_NAME}.v{PROMPT_VERSION}",
        )
