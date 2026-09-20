from __future__ import annotations

import httpx
import pytest
import respx

from scholium.models.base import Message, ModelError
from scholium.models.ollama import OllamaBackend

BASE_URL = "http://localhost:11434"


@respx.mock
def test_chat_returns_text_and_token_counts():
    respx.post(f"{BASE_URL}/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={
                "message": {"role": "assistant", "content": "hello there"},
                "prompt_eval_count": 10,
                "eval_count": 3,
            },
        )
    )
    backend = OllamaBackend(BASE_URL)
    result = backend.chat([Message(role="user", content="hi")], model="llama3.1:8b")
    assert result.text == "hello there"
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 3
    assert result.backend == "ollama"


@respx.mock
def test_chat_json_mode_parses_content():
    respx.post(f"{BASE_URL}/api/chat").mock(
        return_value=httpx.Response(
            200, json={"message": {"content": '{"score": 4, "reason": "ok"}'}}
        )
    )
    backend = OllamaBackend(BASE_URL)
    result = backend.chat(
        [Message(role="user", content="hi")], model="m", json_schema={"type": "object"}
    )
    assert result.parsed == {"score": 4, "reason": "ok"}


@respx.mock
def test_chat_json_mode_raises_on_invalid_json():
    respx.post(f"{BASE_URL}/api/chat").mock(
        return_value=httpx.Response(200, json={"message": {"content": "not json"}})
    )
    backend = OllamaBackend(BASE_URL)
    with pytest.raises(ModelError):
        backend.chat(
            [Message(role="user", content="hi")], model="m", json_schema={"type": "object"}
        )


@respx.mock
def test_embed_returns_vector_and_dim():
    respx.post(f"{BASE_URL}/api/embeddings").mock(
        return_value=httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3]})
    )
    backend = OllamaBackend(BASE_URL)
    result = backend.embed(["some text"], model="specter2")
    assert result.vectors == [[0.1, 0.2, 0.3]]
    assert result.dim == 3


@respx.mock
def test_server_error_retries_then_raises_model_error():
    route = respx.post(f"{BASE_URL}/api/chat").mock(return_value=httpx.Response(500))
    backend = OllamaBackend(BASE_URL, max_retries=2)
    with pytest.raises(ModelError):
        backend.chat([Message(role="user", content="hi")], model="m")
    assert route.call_count == 2


def test_rerank_is_not_implemented_directly():
    backend = OllamaBackend(BASE_URL)
    with pytest.raises(NotImplementedError):
        backend.rerank("q", ["d1"], model="m")
