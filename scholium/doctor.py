"""The doctor subcommand: report what is reachable and what is missing.

doctor never raises on a failing check. It reports every check and exits non-zero
if any required one failed, so it is safe to run on a half-configured machine.
That is the whole point of it, plan section 5.2.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from scholium.config import Config

OK = "ok"
WARN = "warn"
FAIL = "fail"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    required: bool = True


def _host_port(dsn: str) -> tuple[str, int]:
    parsed = urlparse(dsn)
    return parsed.hostname or "localhost", parsed.port or 5432


def check_config(config: Config) -> list[Check]:
    checks = [
        Check("config root", OK, str(config.root)),
        Check(
            "contact email",
            OK if config.contact.email else WARN,
            config.contact.email
            or "unset; OpenAlex, Crossref and Unpaywall want a polite-pool email",
            required=False,
        ),
    ]
    local = config.root / "config.local.toml"
    checks.append(
        Check(
            "config.local.toml",
            OK if local.exists() else WARN,
            "present" if local.exists() else "missing; copy config.local.toml.example",
            required=False,
        )
    )
    return checks


def check_store(config: Config, *, timeout: float = 2.0) -> list[Check]:
    host, port = _host_port(config.store.dsn)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            reachable = True
    except OSError as exc:
        return [Check("postgres", FAIL, f"{host}:{port} unreachable ({exc.__class__.__name__})")]
    checks = [Check("postgres", OK, f"{host}:{port} reachable")] if reachable else []

    try:
        import psycopg
    except ImportError:
        checks.append(
            Check("pgvector", WARN, "psycopg not installed, cannot verify", required=False)
        )
        return checks

    try:
        with psycopg.connect(config.store.dsn, connect_timeout=int(timeout)) as conn:
            row = conn.execute(
                "select extversion from pg_extension where extname = 'vector'"
            ).fetchone()
            version = conn.execute("select current_setting('server_version')").fetchone()
            checks.append(Check("postgres version", OK, str(version[0]) if version else "unknown"))
            if row:
                checks.append(Check("pgvector", OK, f"extension loaded, version {row[0]}"))
            else:
                checks.append(Check("pgvector", FAIL, "extension not loaded in this database"))
            checks.extend(_check_store_contents(conn))
    except Exception as exc:
        checks.append(Check("pgvector", FAIL, f"{exc.__class__.__name__}: {exc}"))
    return checks


def _check_store_contents(conn) -> list[Check]:
    """Row counts per table and the last run per tool, per plan section 5.2
    Day 12 to 14: "The doctor command reports store version, row counts, last
    run per tool." Never required: an empty, freshly migrated store is a
    normal state, and a store that has not been migrated yet is reported as
    a warning here rather than failing doctor outright, since `pgvector` above
    already carries the hard failure for that case.
    """
    try:
        tables_row = conn.execute(
            "select count(*) from information_schema.tables "
            "where table_schema = 'public' and table_name = 'paper'"
        ).fetchone()
    except Exception as exc:
        return [Check("store contents", WARN, f"could not inspect: {exc}", required=False)]
    if not tables_row or not tables_row[0]:
        return [
            Check(
                "store contents",
                WARN,
                "schema not migrated yet; run `alembic upgrade head`",
                required=False,
            )
        ]

    counts = []
    for table in ("paper", "project", "candidate", "label", "extraction", "run"):
        try:
            n = conn.execute(f"select count(*) from {table}").fetchone()[0]
            counts.append(f"{table}={n}")
        except Exception:
            counts.append(f"{table}=?")
    checks = [Check("store row counts", OK, ", ".join(counts), required=False)]

    try:
        rows = conn.execute(
            "select tool, max(started_at) from run group by tool order by tool"
        ).fetchall()
    except Exception:
        rows = []
    detail = ", ".join(f"{tool}: {started}" for tool, started in rows) if rows else "no runs yet"
    checks.append(Check("last run per tool", OK, detail, required=False))
    return checks


def check_ollama(config: Config, *, timeout: float = 2.0) -> list[Check]:
    base = config.models.ollama.base_url.rstrip("/")
    try:
        response = httpx.get(f"{base}/api/tags", timeout=timeout)
        response.raise_for_status()
        names = [m.get("name", "?") for m in response.json().get("models", [])]
    except Exception as exc:
        installed = shutil.which("ollama")
        detail = f"{base} not responding ({exc.__class__.__name__})"
        if installed:
            detail += "; binary is installed, try `ollama serve`"
        return [Check("ollama", FAIL, detail)]
    if not names:
        return [Check("ollama", WARN, f"{base} up, no models pulled", required=False)]
    return [Check("ollama", OK, f"{len(names)} model(s): {', '.join(sorted(names)[:6])}")]


def check_gpu() -> list[Check]:
    if not shutil.which("nvidia-smi"):
        return [Check("gpu", WARN, "nvidia-smi not found", required=False)]
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.free,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
    except Exception as exc:
        return [Check("gpu", WARN, f"nvidia-smi failed: {exc.__class__.__name__}", required=False)]
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    if not lines:
        return [Check("gpu", WARN, "no GPU reported", required=False)]
    name, free, total = (part.strip() for part in lines[0].split(","))
    return [Check("gpu", OK, f"{name}, {free} MiB free of {total} MiB", required=False)]


def check_clients(config: Config, *, timeout: float = 4.0) -> list[Check]:
    """One reachability probe per configured client. Never required: APIs go down."""
    checks: list[Check] = []
    for name in sorted(config.clients):
        client = config.clients[name]
        host = urlparse(client.base_url).hostname or client.base_url
        try:
            socket.getaddrinfo(host, None)
        except OSError:
            checks.append(Check(f"client {name}", WARN, f"{host} does not resolve", required=False))
            continue
        checks.append(
            Check(f"client {name}", OK, f"{host}, {client.rate_per_second}/s", required=False)
        )
    return checks


def run(config: Config) -> list[Check]:
    return [
        *check_config(config),
        *check_store(config),
        *check_ollama(config),
        *check_gpu(),
        *check_clients(config),
    ]
