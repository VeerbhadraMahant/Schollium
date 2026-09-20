# STATUS

Last updated: 2026-09-20 (Phase 0 built end to end; live-database verification not yet run on this machine)

## Current phase

Phase 0: Foundation. See docs/plan/01_Foundation_Phase0.md section 5.

The day-by-day and week-by-week schedule in plan sections 4 and 5.2 is not being followed. It was sized for 8 to 12 hours per week alongside coursework and no longer matches how the work is actually happening. Dates and day labels are dropped.

What is kept: the dependency order within Phase 0, and the checklist below as the gate. Order is skeleton and config, then store, then clients, then model layer, then run logging, because each stage depends on the one before it. Phase 1 does not start until every box below is ticked. Plan section 3.6 still applies in spirit: slipping is fine, skipping evaluation is not.

Everything below is written and passes what can be verified without Docker: 154 offline tests, `ruff check` and `ruff format` clean, imports clean. Docker was not available in the environment this was built in, so the nine tests that need a real Postgres (marked `store`) and the `doctor` postgres/pgvector/row-count checks have not been run live yet. **Next item: run the verification steps below on a machine with Docker and Ollama, then tick the two boxes that need it.**

## Phase 0 checklist

- [x] Repository created, package skeleton, pyproject with console entry point `scholium`
- [x] ruff config and pre-commit hook
- [x] docker-compose.yml with pgvector-enabled Postgres (`pgvector/pgvector:pg17`) and a named volume
- [x] Config loader (config.toml, config.local.toml, env overrides) validated by Pydantic settings — unknown keys fail loudly, tested
- [x] `doctor` subcommand: Postgres reachable, pgvector loaded, Ollama models, VRAM (via nvidia-smi), store version, row counts, last run per tool
- [x] Alembic migrations for the full schema in plan section 2.2 (vector extension, HNSW index, tsvector plus GIN, JSONB columns) — all 13 tables, checked against `scholium/store/schema.py` by an offline test so the two cannot silently drift apart
- [x] Canonical ID normalization with at least 25 test cases including ugly ones — 54 cases in `tests/store/test_ids.py`, including the 10.48550 arXiv-DOI folding case the plan calls out by name
- [x] Upsert semantics tested (never overwrite filled with empty) — logic built into `upsert_paper`; **offline-verified as far as the generated SQL and code path go, live-verified only once the `store`-marked test runs against real Postgres**
- [x] Typed accessors for every table plus two similarity helpers — `nearest_papers` is implemented against `paper_embedding`; `nearest_chunks` intentionally raises `NotImplementedError` with a clear message, because the chunk table it needs belongs to Read (Phase 1, plan section 7.4), not Phase 0's schema (plan section 2.2). This is a deliberate partial, not an oversight — see `scholium/store/accessors.py`.
- [x] Clients: openalex, semanticscholar, arxiv, pubmed, europepmc, crossref, unpaywall, dblp, each with rate limiter (token bucket), retries (tenacity, backoff on 429/5xx), disk cache keyed by URL, and cassette tests (respx-mocked, offline) — 37 tests across the 8 clients
- [x] Model layer: chat with JSON schema, embed, rerank; Ollama backend; OpenAI-compatible backend; SPECTER2 embedding backend (lazy-imports `sentence-transformers`, the `embed` extra); stub backend; step registry from config, with a logged fallback to the default when a step is unconfigured
- [x] Run context manager writing run rows with config snapshot (API keys redacted before storage, since plan section 13.4 later exports this to a git-committed JSONL) and git hash — deliberately uses its own short connections for the run row itself, separate from the tool body's connection, so a failed run's own "failed" status survives even when the tool's substantive writes roll back; tested live
- [ ] **End-to-end smoke test: search OpenAlex, upsert 10 papers, embed, store, read back — written (`tests/store/test_store_live.py::test_end_to_end_smoke`), not yet run live**
- [x] Offline test suite under two minutes — 154 tests in about 20 seconds
- [x] README quickstart: install, docker compose up, create config.local, run doctor

## How to verify the parts that need Docker

Nothing here was skipped; it just could not be run in the environment this was built in. On a machine with Docker and Ollama:

```bash
git pull
python -m venv .venv && .venv/Scripts/activate      # or source .venv/bin/activate
pip install -e ".[dev]"

docker compose up -d
docker compose ps                       # wait for postgres to report healthy

alembic upgrade head                    # applies the schema; check it in a client if you want:
                                         #   docker compose exec postgres psql -U scholium -d scholium -c "\dt"

pytest -m store                         # 9 tests: migration, upsert-never-overwrites-filled,
                                         # nearest_papers ordering, run_context durability under
                                         # rollback, the end-to-end smoke test, and doctor's
                                         # store-contents reporting — all against a real,
                                         # throwaway Postgres via testcontainers

cp config.local.toml.example config.local.toml   # fill in contact.email at least
scholium doctor                         # postgres, pgvector, row counts and last-run-per-tool
                                         # should now all show [ok]; ollama will show [warn] or
                                         # [FAIL] until you `ollama serve` and pull a model
```

If `pytest -m store` passes and `scholium doctor` shows no `[FAIL]` lines (warnings for Ollama are fine until it is running), tick the two remaining boxes above and this phase's gate is green.

## Phase gates

| Phase | Gate | Status |
| --- | --- | --- |
| 0 Foundation | checklist above green | built, 2 of 15 items pending live Docker verification |
| 1 Discovery | Find recall 80 percent on 20 held-out; Read field accuracy 90 percent on 20 papers | not started |
| 2 Writing chain | one real section through Plan, Write, Cite with 100 percent valid citation keys | not started |
| 3 Presentation and review | Figures 5 of 5 specs run; Check finds all 18 planted issues | not started |
| 4 Integration | full run on the honors project with every gate exercised | not started |
| 5 Hardening | README quickstart works on a fresh machine | not started |

## Eval scores

| Tool | Metric | Latest score | Date | Commit |
| --- | --- | --- | --- | --- |
| Find | recall at 200 | not run | | |
| Read | field accuracy | not run | | |
| Plan | gaps found of 3 | not run | | |
| Write | valid keys, claims coverage | not run | | |
| Cite | precision, recall on flagged | not run | | |
| Figures | specs run | not run | | |
| Check | planted issues found | not run | | |

## Decisions log (pointer)

See docs/adr/. Current: 0001 Postgres with pgvector as the shared store; 0002 expanded source clients, eight in Phase 0 and four more in Phase 1.

## Open questions

- Which 7B to 8B and 14B to 32B open instruct models to use at Phase 1 start (pick then, record in config and ADR).
- Whether a seed set of 10 or more known-relevant papers exists for the honors project, or Find bootstraps from problem.md alone.
- Which Phase 1 sources from ADR 0002 survive the section 6.7 recall ablation (OpenReview, CORE, Springer Nature, bioRxiv).
