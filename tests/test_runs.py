from __future__ import annotations

from scholium.config import Config
from scholium.runs import current_git_hash, redacted_config_snapshot


def test_redacted_config_snapshot_hides_api_keys():
    config = Config(clients={"semanticscholar": {"base_url": "https://x", "api_key": "secret-123"}})
    snapshot = redacted_config_snapshot(config)
    assert snapshot["clients"]["semanticscholar"]["api_key"] == "***"


def test_redacted_config_snapshot_keeps_empty_api_key_as_is():
    config = Config(clients={"openalex": {"base_url": "https://x", "api_key": ""}})
    snapshot = redacted_config_snapshot(config)
    assert snapshot["clients"]["openalex"]["api_key"] == ""


def test_redacted_config_snapshot_hides_nested_openai_key():
    config = Config(models={"openai_compatible": {"base_url": "https://x", "api_key": "sk-abc"}})
    snapshot = redacted_config_snapshot(config)
    assert snapshot["models"]["openai_compatible"]["api_key"] == "***"


def test_redacted_config_snapshot_excludes_root_path():
    config = Config()
    snapshot = redacted_config_snapshot(config)
    assert "root" not in snapshot


def test_redacted_config_snapshot_keeps_non_secret_fields():
    config = Config(contact={"email": "me@example.com"})
    snapshot = redacted_config_snapshot(config)
    assert snapshot["contact"]["email"] == "me@example.com"


def test_current_git_hash_returns_something_in_this_repo():
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    result = current_git_hash(repo_root)
    assert result is None or (isinstance(result, str) and len(result) == 40)


def test_current_git_hash_returns_none_for_non_repo(tmp_path):
    assert current_git_hash(tmp_path) is None
