# Changelog

One line per merged branch, newest first. Format: date, branch, what changed, eval score if the branch touched a tool.

- 2026-09-20 phase0: full Phase 0 build on main — package skeleton, config loader, `doctor`; store (13-table schema, Alembic migration, canonical IDs with 54 test cases, upsert-merge semantics, typed accessors, nearest_papers); model layer (Ollama, OpenAI-compatible, SPECTER2, stub backends, step registry, LLM pointwise reranker); all 8 Phase 0 clients (openalex, semanticscholar, arxiv, pubmed, europepmc, crossref, unpaywall, dblp) with rate limiting, retries, disk cache, cassette tests; run context manager with redacted config snapshots. 154 offline tests in ~20s, ruff clean. 9 `store`-marked tests need Docker and have not run live yet; see docs/STATUS.md for exact verification steps.
- 2026-09-20 docs: ADR 0002, source clients expanded to eight in Phase 0 (adds DBLP and Europe PMC) and four more in Phase 1 (OpenReview, CORE, Springer Nature, bioRxiv).
- 2026-09-19 docs: architecture paragraph corrected to Postgres with pgvector (was a stale SQLite line); removed duplicate root STATUS.md and MIGRATION.md.
- 2026-09-18 docs: initial plan, CLAUDE.md, STATUS.md, ADR 0001 (Postgres with pgvector).
