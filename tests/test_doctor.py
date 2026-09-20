from __future__ import annotations

import httpx
import respx

from scholium import doctor
from scholium.config import Config


def test_check_config_reports_missing_email_as_warning(tmp_path):
    config = Config(root=tmp_path)
    checks = doctor.check_config(config)
    email_check = next(c for c in checks if c.name == "contact email")
    assert email_check.status == doctor.WARN
    assert email_check.required is False


def test_check_config_reports_present_email_as_ok(tmp_path):
    config = Config(root=tmp_path, contact={"email": "me@example.com"})
    checks = doctor.check_config(config)
    email_check = next(c for c in checks if c.name == "contact email")
    assert email_check.status == doctor.OK


def test_check_store_fails_on_unreachable_host():
    config = Config(store={"dsn": "postgresql://u:p@127.0.0.1:1/db"})
    checks = doctor.check_store(config, timeout=0.5)
    assert checks[0].status == doctor.FAIL
    assert checks[0].required is True


@respx.mock
def test_check_ollama_ok_when_models_present():
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "llama3.1:8b"}]})
    )
    config = Config()
    checks = doctor.check_ollama(config)
    assert checks[0].status == doctor.OK
    assert "llama3.1:8b" in checks[0].detail


@respx.mock
def test_check_ollama_warns_when_no_models_pulled():
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": []})
    )
    config = Config()
    checks = doctor.check_ollama(config)
    assert checks[0].status == doctor.WARN
    assert checks[0].required is False


def test_check_ollama_fails_when_unreachable():
    config = Config(models={"ollama": {"base_url": "http://127.0.0.1:1"}})
    checks = doctor.check_ollama(config, timeout=0.5)
    assert checks[0].status == doctor.FAIL
    assert checks[0].required is True


def test_check_clients_never_required(tmp_path):
    config = Config(
        clients={"openalex": {"base_url": "https://api.openalex.org", "rate_per_second": 8.0}}
    )
    checks = doctor.check_clients(config)
    assert all(c.required is False for c in checks)


def test_run_aggregates_all_checks():
    config = Config()
    checks = doctor.run(config)
    names = {c.name for c in checks}
    assert "postgres" in names
    assert "ollama" in names
