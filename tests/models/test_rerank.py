from __future__ import annotations

from pathlib import Path

from scholium.models.base import Message
from scholium.models.rerank import LLMPointwiseReranker
from scholium.models.stub import StubBackend

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def test_reranker_scores_each_document_via_chat():
    query = "conditional diffusion models for MR to CT synthesis"
    documents = ["A paper about exactly that.", "A paper about something else entirely."]
    template = (PROMPTS_DIR / "rerank.pointwise.v1.txt").read_text(encoding="utf-8")

    fixtures = {}
    for doc in documents:
        prompt = template.format(query=query, document=doc)
        score = 5 if "exactly" in doc else 1
        fixtures[prompt] = {"text": f'{{"score": {score}, "reason": "stub reason"}}'}

    backend = StubBackend(chat_fixtures=fixtures)
    reranker = LLMPointwiseReranker(backend, prompts_dir=PROMPTS_DIR)
    result = reranker.rerank(query, documents, model="stub-model")

    assert result.scores == [5.0, 1.0]
    assert all(r == "stub reason" for r in result.reasons)
    assert result.backend == "stub+rerank.pointwise.v1"


def test_prompt_template_has_query_and_document_placeholders():
    template = (PROMPTS_DIR / "rerank.pointwise.v1.txt").read_text(encoding="utf-8")
    filled = template.format(query="Q", document="D")
    assert "Q" in filled
    assert "D" in filled


def test_message_role_default_shape():
    m = Message(role="user", content="hi")
    assert m.role == "user"
    assert m.content == "hi"
