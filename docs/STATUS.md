# STATUS

Last updated: 2026-09-20 (plan committed, ADR 0002 accepted, nothing built yet)

## Current phase

Phase 0: Foundation (weeks 1 to 2, 21 Sep to 4 Oct 2026). See docs/plan/01_Foundation_Phase0.md section 5.

Next item: Day 1 to 2 skeleton (repository, package, pyproject with `scholium` entry point, ruff, pre-commit, config loader, `doctor`).

## Phase 0 checklist

- [ ] Repository created, package skeleton, pyproject with console entry point `scholium`
- [ ] ruff config and pre-commit hook
- [ ] docker-compose.yml with pgvector-enabled Postgres and a named volume
- [ ] Config loader (config.toml, config.local.toml, env overrides) validated by Pydantic settings
- [ ] `doctor` subcommand: Postgres reachable, pgvector loaded, Ollama models, VRAM, store version, row counts
- [ ] Alembic migrations for the full schema in plan section 2.2 (vector extension, HNSW index, tsvector plus GIN, JSONB columns)
- [ ] Canonical ID normalization with at least 25 test cases including ugly ones
- [ ] Upsert semantics tested (never overwrite filled with empty)
- [ ] Typed accessors for every table plus two similarity helpers (nearest papers, nearest chunks within a paper)
- [ ] Clients: openalex, semanticscholar, arxiv, pubmed, europepmc, crossref, unpaywall, dblp, each with rate limiter, retries, disk cache, cassette test (ADR 0002)
- [ ] Model layer: chat with JSON schema, embed, rerank; Ollama backend; OpenAI-compatible backend; SPECTER2 embedding backend; stub backend; step registry from config
- [ ] Run context manager writing run rows with config snapshot and git hash
- [ ] End-to-end smoke test: search OpenAlex, upsert 10 papers, embed, store, read back
- [ ] Offline test suite under two minutes
- [ ] README quickstart: install, docker compose up, create config.local, run doctor

## Phase gates

| Phase | Gate | Status |
| --- | --- | --- |
| 0 Foundation | checklist above green | not started |
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
