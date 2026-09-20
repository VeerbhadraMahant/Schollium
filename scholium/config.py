"""Configuration loading and validation.

Three layers, lowest precedence first: config.toml (checked in), config.local.toml
(gitignored, machine paths and API keys), then environment variables prefixed with
SCHOLIUM_ using __ as the nesting separator.

Every model sets extra="forbid" so a typo in a key fails at startup with the key
name rather than being silently ignored, which is the point of validating here.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

ENV_PREFIX = "SCHOLIUM_"
ENV_NESTED_DELIMITER = "__"

DEFAULT_CONFIG = "config.toml"
LOCAL_CONFIG = "config.local.toml"


class Strict(BaseModel):
    """Base for every config section. Unknown keys are an error, not a warning."""

    model_config = ConfigDict(extra="forbid")


class Paths(Strict):
    data_dir: Path = Path("data")
    prompts_dir: Path = Path("prompts")
    projects_dir: Path = Path("projects")
    cache_dir: Path = Path("data/cache")
    pdf_dir: Path = Path("data/pdfs")


class Store(Strict):
    dsn: str = "postgresql://scholium:scholium@localhost:5433/scholium"


class OllamaBackend(Strict):
    base_url: str = "http://localhost:11434"


class OpenAICompatibleBackend(Strict):
    base_url: str = ""
    api_key: str = ""


class EmbeddingModels(Strict):
    paper_backend: str = "specter2"
    paper_model: str = "allenai/specter2_base"
    chunk_model: str = ""


class Step(Strict):
    """One named model step, for example find.expand. See plan section 2.3."""

    backend: str
    model: str


class Models(Strict):
    default_backend: str = "ollama"
    default_model: str = ""
    ollama: OllamaBackend = Field(default_factory=OllamaBackend)
    openai_compatible: OpenAICompatibleBackend = Field(default_factory=OpenAICompatibleBackend)
    embedding: EmbeddingModels = Field(default_factory=EmbeddingModels)
    steps: dict[str, Step] = Field(default_factory=dict)

    def step(self, name: str) -> Step:
        """Resolve a step name to a backend and model, falling back to the default.

        Callers log the fallback; this function stays pure. Never hardcode a model
        name at a call site, rule 5.
        """
        if name in self.steps:
            return self.steps[name]
        return Step(backend=self.default_backend, model=self.default_model)


class Contact(Strict):
    email: str = ""


class Client(Strict):
    base_url: str
    rate_per_second: float = 1.0
    api_key: str = ""


class Http(Strict):
    timeout_seconds: float = 30.0
    max_retries: int = 4
    cache_enabled: bool = True


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        extra="forbid",
        env_prefix=ENV_PREFIX,
        env_nested_delimiter=ENV_NESTED_DELIMITER,
        case_sensitive=False,
    )

    paths: Paths = Field(default_factory=Paths)
    store: Store = Field(default_factory=Store)
    models: Models = Field(default_factory=Models)
    contact: Contact = Field(default_factory=Contact)
    clients: dict[str, Client] = Field(default_factory=dict)
    http: Http = Field(default_factory=Http)

    # Set by load(); not part of the config surface itself.
    root: Path = Field(default_factory=Path.cwd, exclude=True)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Environment wins over the values passed in from the TOML layers.
        return (env_settings, init_settings)

    def resolve(self, path: Path) -> Path:
        """Make a configured relative path absolute against the repository root."""
        return path if path.is_absolute() else self.root / path


def deep_merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    """Merge overlay onto base. Nested tables merge; scalars and lists replace."""
    out: dict[str, Any] = dict(base)
    for key, value in overlay.items():
        current = out.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            out[key] = deep_merge(current, value)
        else:
            out[key] = value
    return out


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def find_root(start: Path | None = None) -> Path:
    """Walk upwards for the directory holding config.toml. Falls back to cwd."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / DEFAULT_CONFIG).is_file():
            return candidate
    return here


def load(root: Path | None = None, *, env: Mapping[str, str] | None = None) -> Config:
    """Load, merge and validate the three configuration layers.

    Raises pydantic.ValidationError if a key is unknown or a value has the wrong
    type, so a typo fails at startup rather than halfway through a run.
    """
    root = (root or find_root()).resolve()
    merged = deep_merge(_read_toml(root / DEFAULT_CONFIG), _read_toml(root / LOCAL_CONFIG))
    merged["root"] = root

    environ = os.environ if env is None else env
    token = None
    if env is not None:
        # BaseSettings reads os.environ directly, so swap it for the duration.
        token = dict(os.environ)
        os.environ.clear()
        os.environ.update(environ)
    try:
        return Config(**merged)
    finally:
        if token is not None:
            os.environ.clear()
            os.environ.update(token)
