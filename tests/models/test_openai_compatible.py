from __future__ import annotations

import httpx
import pytest
import respx

from scholium.models.base import Message, ModelError
from scholium.models.openai_compatible import OpenAICompatibleBackend

BASE_URL = "https://api.example.com/v1"


@respx.mock
def test_chat_returns_text_and_usage():
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "hi back"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            },
        )
    )
    backend = OpenAICompatibleBackend(BASE_URL, api_key="sk-test")
    result = backend.chat([Message(role="user", content="hi")], model="gpt-test")
    assert result.text == "hi back"
    assert result.prompt_tokens == 5
    assert result.completion_tokens == 2


@respx.mock
def test_chat_sends_bearer_auth_header():
    route = respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    )
    backend = OpenAICompatibleBackend(BASE_URL, api_key="sk-secret")
    backend.chat([Message(role="user", content="hi")], model="m")
    assert route.calls.last.request.headers["Authorization"] == "Bearer sk-secret"


@respx.mock
def test_chat_json_mode_sets_response_format():
    route = respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})
    )
    backend = OpenAICompatibleBackend(BASE_URL)
    backend.chat([Message(role="user", content="hi")], model="m", json_schema={"type": "object"})
    sent = route.calls.last.request.content
    assert b'"response_format"' in sent


@respx.mock
def test_embed_returns_vectors():
    respx.post(f"{BASE_URL}/embeddings").mock(
        return_value=httpx.Response(
            200, json={"data": [{"embedding": [1.0, 2.0]}, {"embedding": [3.0, 4.0]}]}
        )
    )
    backend = OpenAICompatibleBackend(BASE_URL)
    result = backend.embed(["a", "b"], model="text-embed")
    assert result.vectors == [[1.0, 2.0], [3.0, 4.0]]
    assert result.dim == 2


@respx.mock
def test_rate_limit_retries_then_raises():
    route = respx.post(f"{BASE_URL}/chat/completions").mock(return_value=httpx.Response(429))
    backend = OpenAICompatibleBackend(BASE_URL, max_retries=2)
    with pytest.raises(ModelError):
        backend.chat([Message(role="user", content="hi")], model="m")
    assert route.call_count == 2
