from __future__ import annotations

import pytest
from pydantic import ValidationError

from scholium.config import Config, deep_merge, load


def test_default_config_loads_with_no_files(tmp_path):
    config = load(root=tmp_path)
    assert config.store.dsn.startswith("postgresql://")
    assert config.root == tmp_path.resolve()


def test_config_toml_overrides_defaults(tmp_path):
    (tmp_path / "config.toml").write_text(
        '[store]\ndsn = "postgresql://x:y@host:5432/db"\n', encoding="utf-8"
    )
    config = load(root=tmp_path)
    assert config.store.dsn == "postgresql://x:y@host:5432/db"


def test_config_local_toml_overrides_config_toml(tmp_path):
    (tmp_path / "config.toml").write_text(
        '[contact]\nemail = "base@example.com"\n', encoding="utf-8"
    )
    (tmp_path / "config.local.toml").write_text(
        '[contact]\nemail = "local@example.com"\n', encoding="utf-8"
    )
    config = load(root=tmp_path)
    assert config.contact.email == "local@example.com"


def test_unknown_key_fails_loudly(tmp_path):
    (tmp_path / "config.toml").write_text('[store]\ntypo_field = "x"\n', encoding="utf-8")
    with pytest.raises(ValidationError):
        load(root=tmp_path)


def test_unknown_top_level_section_fails_loudly(tmp_path):
    (tmp_path / "config.toml").write_text("[not_a_real_section]\nx = 1\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load(root=tmp_path)


def test_env_var_overrides_toml(tmp_path):
    (tmp_path / "config.toml").write_text(
        '[contact]\nemail = "toml@example.com"\n', encoding="utf-8"
    )
    config = load(root=tmp_path, env={"SCHOLIUM_CONTACT__EMAIL": "env@example.com"})
    assert config.contact.email == "env@example.com"


def test_deep_merge_merges_nested_tables():
    base = {"a": {"x": 1, "y": 2}, "b": 1}
    overlay = {"a": {"y": 3}, "c": 4}
    merged = deep_merge(base, overlay)
    assert merged == {"a": {"x": 1, "y": 3}, "b": 1, "c": 4}


def test_deep_merge_scalar_replaces_not_merges():
    base = {"a": [1, 2, 3]}
    overlay = {"a": [4]}
    assert deep_merge(base, overlay) == {"a": [4]}


def test_step_resolution_falls_back_to_default():
    config = Config(models={"default_backend": "ollama", "default_model": "m1"})
    step = config.models.step("find.expand")
    assert step.backend == "ollama"
    assert step.model == "m1"


def test_step_resolution_uses_configured_override():
    config = Config(
        models={
            "default_backend": "ollama",
            "default_model": "m1",
            "steps": {"find.expand": {"backend": "openai_compatible", "model": "gpt-x"}},
        }
    )
    step = config.models.step("find.expand")
    assert step.backend == "openai_compatible"
    assert step.model == "gpt-x"


def test_resolve_makes_relative_path_absolute_against_root(tmp_path):
    config = load(root=tmp_path)
    resolved = config.resolve(config.paths.data_dir)
    assert resolved == tmp_path / "data"
    assert resolved.is_absolute()
