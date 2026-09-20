"""Resolve a named step (find.expand, read.extract, plan.gap, ...) to a live
backend and a model name, per plan section 2.3 and 5.2 Day 9 to 11.

A step absent from config falls back to the default backend and logs a
warning, per the plan. The model name is never hardcoded at a call site: it
always comes from config, through this function.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

from scholium.config import Config
from scholium.models.base import ModelBackend
from scholium.models.ollama import OllamaBackend
from scholium.models.openai_compatible import OpenAICompatibleBackend
from scholium.models.stub import StubBackend

logger = logging.getLogger(__name__)


class ResolvedStep(NamedTuple):
    backend: ModelBackend
    model: str


def build_backend(config: Config, backend_name: str) -> ModelBackend:
    if backend_name == "ollama":
        return OllamaBackend(
            config.models.ollama.base_url,
            timeout=config.http.timeout_seconds,
            max_retries=config.http.max_retries,
        )
    if backend_name == "openai_compatible":
        return OpenAICompatibleBackend(
            config.models.openai_compatible.base_url,
            api_key=config.models.openai_compatible.api_key,
            timeout=config.http.timeout_seconds,
            max_retries=config.http.max_retries,
        )
    if backend_name == "stub":
        return StubBackend()
    raise ValueError(f"unknown model backend {backend_name!r}")


def resolve_step(config: Config, step_name: str) -> ResolvedStep:
    """Look up a step in config.models.steps. Falls back to the configured
    default backend and model, and logs that fallback, rather than failing.
    """
    if step_name not in config.models.steps:
        logger.warning(
            "model step %r is not configured; falling back to the default backend %r",
            step_name,
            config.models.default_backend,
        )
    step = config.models.step(step_name)
    return ResolvedStep(backend=build_backend(config, step.backend), model=step.model)
