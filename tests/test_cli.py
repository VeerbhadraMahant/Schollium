from __future__ import annotations

import httpx
import respx

from scholium.cli import main


def test_no_command_prints_help_and_exits_nonzero(capsys):
    exit_code = main([])
    assert exit_code == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_version_flag(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert "scholium" in capsys.readouterr().out.lower()


@respx.mock
def test_doctor_command_runs_and_reports(tmp_path, capsys):
    (tmp_path / "config.toml").write_text(
        '[store]\ndsn = "postgresql://u:p@127.0.0.1:1/db"\n', encoding="utf-8"
    )
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": []})
    )
    exit_code = main(["--root", str(tmp_path), "doctor"])
    out = capsys.readouterr().out
    assert "postgres" in out
    assert exit_code == 1  # postgres check is required and unreachable
