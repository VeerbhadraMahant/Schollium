from __future__ import annotations

import pytest

from scholium.models.base import Message, ModelError
from scholium.models.stub import StubBackend


def test_chat_returns_fixture_by_key():
    backend = StubBackend(chat_fixtures={"hello": {"text": "world"}})
    result = backend.chat([Message(role="user", content="hello")], model="stub-model")
    assert result.text == "world"
    assert result.backend == "stub"
    assert result.model_name == "stub-model"


def test_chat_falls_back_to_default_fixture():
    backend = StubBackend(chat_fixtures={"default": {"text": "generic"}})
    result = backend.chat([Message(role="user", content="anything")], model="m")
    assert result.text == "generic"


def test_chat_raises_when_no_fixture_matches():
    backend = StubBackend(chat_fixtures={})
    with pytest.raises(ModelError):
        backend.chat([Message(role="user", content="unknown")], model="m")


def test_chat_parses_json_when_schema_given():
    backend = StubBackend(chat_fixtures={"q": {"text": '{"score": 4, "reason": "close match"}'}})
    result = backend.chat(
        [Message(role="user", content="q")], model="m", json_schema={"type": "object"}
    )
    assert result.parsed == {"score": 4, "reason": "close match"}


def test_chat_raises_on_invalid_json_when_schema_required():
    backend = StubBackend(chat_fixtures={"q": {"text": "not json"}})
    with pytest.raises(ModelError):
        backend.chat([Message(role="user", content="q")], model="m", json_schema={"type": "object"})


def test_embed_is_deterministic():
    backend = StubBackend(embed_dim=16)
    a = backend.embed(["same text"], model="m")
    b = backend.embed(["same text"], model="m")
    assert a.vectors == b.vectors
    assert a.dim == 16


def test_embed_different_text_different_vector():
    backend = StubBackend()
    a = backend.embed(["alpha"], model="m")
    b = backend.embed(["beta"], model="m")
    assert a.vectors != b.vectors


def test_rerank_scores_by_term_overlap():
    backend = StubBackend()
    result = backend.rerank(
        "conditional diffusion medical imaging",
        ["conditional diffusion for MR to CT synthesis", "completely unrelated topic about birds"],
        model="m",
    )
    assert result.scores[0] > result.scores[1]
