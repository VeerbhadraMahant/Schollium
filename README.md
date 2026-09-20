# Scholium

A modular, local-first research assistant: seven command-line tools (find, read, plan, write, cite, figures, check) over one shared Postgres store, with a human review step between every tool.

Status: Phase 0 (foundation) built, verification pending. See `docs/STATUS.md`.

- Plan: `docs/plan/` (start with `00_Scholium_Full_Execution_Plan.md`)
- Working with Claude Code: `CLAUDE.md` and `docs/MIGRATION.md`
- Decisions: `docs/adr/`
- Why this exists: `docs/research/landscape-survey-condensed.md`

## Quickstart

Prerequisites: Python 3.11 or newer, Docker with Compose, [Ollama](https://ollama.com) with at least one instruct model pulled, git.

```bash
# 1. Install the package and its dev dependencies
python -m venv .venv
.venv/Scripts/activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -e ".[dev]"       # add ,embed for SPECTER2, ,pdf for PDF parsing when you need them

# 2. Start Postgres with pgvector
docker compose up -d
docker compose ps             # wait for postgres to report healthy

# 3. Configure
cp config.local.toml.example config.local.toml
# edit config.local.toml: set contact.email, and clients.semanticscholar.api_key if you have one

# 4. Apply the schema
alembic upgrade head

# 5. Pull a local model if you have not already
ollama pull llama3.1:8b       # or whatever fits your VRAM; nothing is hardcoded

# 6. Check everything is wired up
scholium doctor
```

`doctor` reports Postgres reachability and pgvector, Ollama and its pulled models, free GPU memory, and which client hosts resolve. It never fails silently: every check prints its own status, and the command exits non-zero only if a *required* check (Postgres reachable, pgvector loaded) failed.

## Development

```bash
pip install -e ".[dev]"
pre-commit install            # runs ruff and the offline test suite on every commit

ruff check .                  # lint
ruff format .                 # format
pytest -m "not store and not live"   # offline suite: no Docker needed, under a minute
pytest -m store                      # store tests: needs Docker (spins up a throwaway Postgres)
```

The offline suite covers canonical ID normalization, config loading, the model layer (Ollama and OpenAI-compatible backends via mocked HTTP, the stub backend, the SPECTER2 backend's caching logic), all eight source clients (via recorded/mocked responses, no network), and `doctor`/`cli`. It does not touch a database. The `store`-marked suite spins up a real, throwaway Postgres via testcontainers, applies the Alembic migration, and exercises upserts, the similarity helper, and the run context manager against it — see `docs/STATUS.md` for how to verify this half by hand.
