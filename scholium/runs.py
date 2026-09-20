"""The run context manager every subcommand uses, per plan section 2.6 and
CLAUDE.md: "Every subcommand runs inside the run context manager, which
writes a run row with config snapshot, git hash, model names, prompt versions
and stats."

The config snapshot is redacted before it is stored. Plan section 13.4 commits
a daily JSONL export of the store's tables to git, and the run table's
config_snapshot column would go straight into that export, so an API key
captured here would end up committed to a repository. Redaction happens once,
here, rather than trusting every future export path to remember to do it.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from scholium.config import Config
from scholium.store import accessors
from scholium.store.db import connection as store_connection
from scholium.store.records import RunRecord

REDACT_KEYS = {"api_key"}
REDACTED = "***"


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: (REDACTED if k in REDACT_KEYS and v else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def redacted_config_snapshot(config: Config) -> dict[str, Any]:
    raw = config.model_dump(mode="json", exclude={"root"})
    return _redact(raw)


def current_git_hash(root) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None


@dataclass
class RunHandle:
    """What the `with run_context(...) as run:` block gets. `run.stats` is a
    plain dict the tool fills in as it goes; it is written back on exit."""

    record: RunRecord
    stats: dict[str, Any] = field(default_factory=dict)


@contextmanager
def run_context(config: Config, *, tool: str, project_id=None) -> Iterator[RunHandle]:
    """Opens a run row, snapshots config and git hash. On a clean exit the run
    is marked finished with whatever stats the caller accumulated; on an
    exception it is marked failed with those same stats, and the exception
    propagates. A run row always exists for what was attempted, even a run
    that crashed halfway through, per plan section 2.6.

    Deliberately does not take the caller's connection. The three writes here
    (open, then finish as finished or failed) each commit on their own, in a
    connection scholium.store.db.connection opens and closes for that one
    write. If they shared a connection and transaction with the tool's own
    work, a tool that raised inside the block would roll back not just its
    own writes but the "this run failed" row meant to record exactly that,
    which defeats the point of writing it. Bookkeeping durability and the
    tool's data durability are two different guarantees and must not share a
    transaction.
    """
    with store_connection(config) as conn:
        record = accessors.insert_run(
            conn,
            RunRecord(
                project_id=project_id,
                tool=tool,
                git_hash=current_git_hash(config.root),
                config_snapshot=redacted_config_snapshot(config),
            ),
        )
    handle = RunHandle(record=record)
    try:
        yield handle
    except Exception:
        with store_connection(config) as conn:
            accessors.finish_run(conn, record.id, status="failed", stats=handle.stats)
        raise
    else:
        with store_connection(config) as conn:
            accessors.finish_run(conn, record.id, status="finished", stats=handle.stats)
