from __future__ import annotations

import logging

import pytest

from scholium.config import Config
from scholium.models.ollama import OllamaBackend
from scholium.models.registry import build_backend, resolve_step


def test_build_backend_ollama():
    config = Config()
    backend = build_backend(config, "ollama")
    assert isinstance(backend, OllamaBackend)


def test_build_backend_unknown_raises():
    config = Config()
    with pytest.raises(ValueError):
        build_backend(config, "not-a-real-backend")


def test_resolve_step_falls_back_to_default_and_warns(caplog):
    config = Config(models={"default_backend": "ollama", "default_model": "llama3.1:8b"})
    with caplog.at_level(logging.WARNING):
        resolved = resolve_step(config, "find.expand")
    assert resolved.model == "llama3.1:8b"
    assert isinstance(resolved.backend, OllamaBackend)
    assert any("find.expand" in r.message for r in caplog.records)


def test_resolve_step_uses_configured_step_without_warning(caplog):
    config = Config(
        models={
            "default_backend": "ollama",
            "default_model": "default-model",
            "steps": {"find.expand": {"backend": "ollama", "model": "specific-model"}},
        }
    )
    with caplog.at_level(logging.WARNING):
        resolved = resolve_step(config, "find.expand")
    assert resolved.model == "specific-model"
    assert not any("find.expand" in r.message for r in caplog.records)
