---
title: "Scholium. Phase 0: Foundation"
author: "Veerbhadra Mahant"
date: "18 September 2026"
---

Sections 2, 3 and 5 of the full plan: the architecture and method every tool depends on, and the two-week foundation build.

## 2. Overall architecture

A single Python package over one shared PostgreSQL store with pgvector, a thin API-client layer, one model interface, and one subpackage per tool. Nothing else is shared between tools; everything passes through the store. The store is the only coupling point, which is what keeps each tool usable alone and the final merge cheap.

### 2.1 Repository layout

| Path | Purpose | Owner phase |
| --- | --- | --- |
| pyproject.toml | Package metadata, single entry point command `scholium` | 0 |
| scholium/config.py | Loads one TOML config: paths, model per step, API keys, rate limits | 0 |
| scholium/store/ | Schema, migrations, typed access functions for every table | 0 |
| scholium/clients/ | One module per external API: openalex, semanticscholar, arxiv, pubmed, crossref, unpaywall | 0 |
| scholium/models/ | Model interface: chat, embed, rerank; backends for Ollama and OpenAI-compatible APIs | 0 |
| scholium/common/ | Paper ID normalization, dedup, text cleaning, PDF parsing, LaTeX helpers | 0 and 2 |
| scholium/find/ | Tool 1 | 1 |
| scholium/read/ | Tool 2 | 1 |
| scholium/plan/ | Tool 3 | 2 |
| scholium/write/ | Tool 4 | 2 |
| scholium/cite/ | Tool 5 | 2 |
| scholium/figures/ | Tool 6 | 3 |
| scholium/check/ | Tool 7 | 3 |
| scholium/orchestrate/ | Pipeline runner, only in Phase 4 | 4 |
| prompts/ | One text file per prompt, versioned, never inline in code | all |
| eval/ | Fixed evaluation sets and scoring scripts per tool | all |
| tests/ | Unit tests per module, integration test per tool | all |
| projects/ | One folder per research project: problem.md, seeds.txt, notes, drafts | user data, gitignored except templates |
| data/ | PDFs and caches; gitignored. Postgres data lives in the Docker volume; docker-compose.yml at the repo root defines the postgres and optional GROBID services | user data |

### 2.2 The shared store

PostgreSQL 16 or newer with the pgvector extension, run locally through Docker Compose with a named volume. Chosen over SQLite because pgvector puts nearest-neighbour search inside the database (no separate numpy or FAISS index to keep in sync), built-in full-text search gives a fourth local keyword channel over stored abstracts and chunks, JSONB columns hold run snapshots and channel metadata queryably, and real concurrency means a later review web view and a running tool can write at the same time. The cost is setup: one docker compose up, a connection string in config.local.toml, and pg_dump instead of copying a file for backups. Schema changes go through Alembic migrations only. Access through psycopg 3 with SQLAlchemy Core (not the ORM) so every query is explicit and typed.

**Canonical paper ID rule.** Lowercase DOI if present. Else arXiv ID without version suffix. Else PubMed ID. Else an OpenAlex work ID. Else a hash of normalized title plus first author surname plus year. Every table references this one ID.

| Table | Key columns | Written by | Read by |
| --- | --- | --- | --- |
| paper | id, doi, arxiv_id, pmid, openalex_id, s2_id, title, abstract, year, venue, authors (json), oa_url, pdf_path, bibtex, created_at | find, cite | all |
| paper_embedding | paper_id, model_name, vector (pgvector, HNSW index, cosine), dim | find, read | find, plan |
| project | id, name, problem_statement, created_at | user via CLI | all |
| candidate | project_id, paper_id, run_id, channels (json), fusion_score, rerank_score, rerank_reason | find | find, read |
| label | project_id, paper_id, label (relevant, irrelevant, maybe), note, labeled_at | user via review view | find, read, plan |
| run | id, project_id, tool, started_at, finished_at, config_snapshot (json), stats (json) | every tool | check, orchestrate |
| citation_edge | citing_id, cited_id, source | find | find, plan |
| extraction | paper_id, project_id, field, value, evidence_span, page, confidence, model_name | read | plan, write, check |
| plan | project_id, version, section, content, status (proposed, edited, approved) | plan | write, check |
| draft | project_id, section, version, latex, cite_keys (json), status | write | cite, figures, check |
| cite_check | draft_id, cite_key, resolves, supports_score, retracted, issue | cite | check |
| figure | project_id, name, script_path, source_result, status | figures | write, check |
| review | draft_id, version, criterion, severity, comment, evidence_ref | check | user |

**Why evidence_span everywhere.** Every extracted or checked fact stores the exact text span and page it came from. This is what makes tools 3, 4 and 7 auditable and is the difference between a research tool and a chatbot.

### 2.3 Model layer

One interface with three operations: chat (messages in, text out, with optional JSON schema enforcement), embed (texts in, vectors out), rerank (query plus documents in, scores out). Two backends: Ollama (local) and any OpenAI-compatible HTTP endpoint (covers OpenAI, Anthropic via a proxy, Gemini, vLLM, LM Studio).

Config maps each named step to a backend and model. Example steps: find.expand, find.rerank, read.extract, plan.gap, plan.critique, write.section, cite.support, check.review. Default for every step is local. Cost and token counts are logged per run.

| Role | Default local model (24 GB VRAM) | When to switch to API |
| --- | --- | --- |
| Embeddings | SPECTER2 base via sentence-transformers, CPU or GPU | never; local is the standard for scientific text |
| Query expansion, reranking | 7B to 8B instruct model, quantized (Qwen2.5 or Llama 3.1 class) | never |
| Extraction | 8B to 14B instruct with JSON mode | if field accuracy is below 85 percent on the eval set |
| Planning, gap analysis | 14B to 32B quantized | frontier model recommended; novelty reasoning is the weakest local skill |
| Section drafting | 14B quantized | frontier model recommended for final drafts, local for first drafts |
| Critique | 14B to 32B quantized | frontier model recommended |

Specific model names are deliberately not fixed here. Open-weight leaderboards move monthly. Choose the best instruct model that fits in VRAM at 4 to 5 bit quantization at the time each phase starts, and record the choice in the run's config snapshot.

### 2.4 Prompt management

Every prompt lives in prompts/ as a text file with a version number in its filename. Code loads by name and version. A prompt change is a commit and shows up in run config snapshots. Never edit a prompt inline while debugging without bumping the version; otherwise evaluation results cannot be compared.

### 2.5 Configuration and secrets

One config.toml checked in with defaults. One config.local.toml, gitignored, for API keys and machine paths. Environment variables override both. Rate limits per client are in config so they can be tuned without code changes.

### 2.6 Logging and reproducibility

Every tool invocation creates a run row with a full config snapshot, git commit hash, model names, prompt versions, and counts (candidates found, tokens used, API calls made). A run can be replayed from its snapshot. This is cheap to build in Phase 0 and impossible to retrofit.

## 3. Development method

Main always runs. Each tool is built on a short-lived branch, merged the day it writes valid store rows, then hardened on main through small follow-up branches. Every tool ships with an evaluation set before it ships with features.

### 3.1 Branching model

1. Phase 0 (foundation) is committed directly to main in small commits. Nothing else may start until Phase 0's checklist in section 5 is green.
2. Each tool gets a branch named tool/find, tool/read, and so on. The branch exists only until the tool's minimal vertical slice works end to end: read inputs from the store, call the model layer, write outputs to the store. Then it merges.
3. After the merge, every improvement to that tool is a branch named tool/find-rerank, tool/find-pubmed, etc., each merged within a week.
4. A branch older than 14 days is a smell. Either merge it behind a feature flag or delete it.
5. Never branch a tool off another tool's branch. Always off main. This is what prevents the store schema from forking.

### 3.2 Definition of done per tool

A tool is done for its phase when all of the following hold:

- Runs as a subcommand with documented flags and a `--dry-run` that prints what it would do.
- Writes a run row with config snapshot and stats.
- Has an eval set in eval/ and a scoring script, and meets the pass criterion in its section.
- Has unit tests for pure functions (ID normalization, dedup, parsing) and one integration test against recorded API responses.
- Has its prompts in prompts/ with versions.
- Works fully local with the default model. API mode is tested but optional.
- README section written: what it does, inputs, outputs, known failure modes.

### 3.3 Testing strategy

External APIs are recorded once with a cassette library (VCR-style) so tests run offline and fast. Model calls in tests use a stub backend that returns canned JSON. Only the eval scripts hit real models. Store tests run against a throwaway Postgres (testcontainers, or a second service in docker compose) migrated fresh per test session and wrapped in a rolled-back transaction per test. This keeps the test suite under two minutes and stops flaky failures from API rate limits.

### 3.4 Evaluation discipline

Each tool has a fixed eval set built from your own honors research:

| Tool | Eval set | Metric | Pass |
| --- | --- | --- | --- |
| Find | 30 known-relevant papers, held out, never used as seeds | recall at 200 candidates | 80 percent |
| Read | 20 papers with hand-filled extraction fields | field accuracy | 90 percent |
| Plan | 3 problem statements with your own gap analysis | overlap of identified gaps, judged by you | 2 of 3 major gaps found |
| Write | 5 sections you already wrote | citation validity, factual consistency with extractions | 100 percent valid keys, no contradiction |
| Cite | 100 citation sentences, 20 deliberately wrong | precision and recall on flagged citations | 90 percent both |
| Figures | 5 result tables | script runs, figure matches spec | 5 of 5 run |
| Check | 3 drafts with known planted issues | issues found | all planted issues found |

Run the eval after every merge to that tool. Record the score in a small results table committed to eval/. A regression blocks the merge.

### 3.5 Coding conventions

- Python 3.11 or newer. Type hints everywhere. Pydantic models for every store record and every model-layer JSON output.
- No global state. Every function takes a store handle and a config object.
- Every model call returns a typed object or raises. Never parse free text with regex when JSON mode is available.
- Any function that calls an external API must accept a client object so tests can inject a recorded one.
- Formatting with ruff. A pre-commit hook runs ruff and the fast tests.

### 3.6 Working cadence

The suite is a side project next to coursework, an internship and club work. The plan assumes 8 to 12 focused hours per week, concentrated on weekends. Each phase below is sized to that. If a week yields under 4 hours, the timeline slips a week; do not compress the next week to catch up. Slipping is fine; skipping evaluation is not.

### 3.7 Documentation

One README at the root with install and a five-minute quickstart. One docs/ page per tool, written when the tool merges, updated when its flags change. A CHANGELOG with one line per merged branch. Architecture decisions that change section 2 get a short ADR file in docs/adr/ stating the decision, the reason and what it replaces.

## 5. Phase 0: foundation (weeks 1 to 2)

Two weeks producing no user-visible feature and every piece of shared infrastructure. Skipping or rushing this phase is the single decision most likely to make the later merge painful.

### 5.1 Why a full foundation before any tool

Every tool needs the same four things: a store to read and write, clients to talk to APIs, a model to call, and a way to log what happened. Building these inside Find and then extracting them later means Find's assumptions leak into the shared code. Building them first, with tests, means Find is only Find.

### 5.2 Step by step

**Day 1 to 2: skeleton.**

1. Create the repository, a Python package, pyproject with one console entry point, ruff config, pre-commit.
2. Write config loading: config.toml defaults, config.local.toml overrides, environment overrides. Validate with a Pydantic settings model so a typo in a key fails loudly at startup.
3. Add a `doctor` subcommand that prints which APIs are reachable, which models are available in Ollama, VRAM free, and where the store lives. You will run this constantly.

**Day 3 to 5: store.**

1. Write docker-compose.yml with a pgvector-enabled Postgres image and a named volume. Write the schema from section 2.2 as Alembic migrations, including the vector extension, the HNSW index on paper_embedding, a tsvector column plus GIN index on paper title and abstract, and JSONB for channels, config_snapshot and stats.
2. Implement the canonical ID function and its tests: DOI lowercasing and prefix stripping, arXiv version stripping, old-style arXiv IDs, PMIDs, OpenAlex IDs, and the fallback title hash. Include ugly real cases: DOIs with uppercase letters, arXiv IDs inside DOIs (10.48550), titles with LaTeX and unicode.
3. Implement upsert semantics: inserting a paper that already exists merges non-null fields and never overwrites a filled abstract with an empty one.
4. Implement typed accessors for every table with SQLAlchemy Core and Pydantic records. No SQL outside scholium/store. Include two similarity helpers here (nearest papers to a vector, nearest chunks within a paper) so no tool writes its own vector query.

**Day 6 to 8: clients.**

One module per API, each with the same shape: a search function, a get-by-id function, and where applicable references and citations functions. Each returns Pydantic records already mapped to store fields.

| Client | Key endpoints | Free tier limits (as of Sept 2026, verify) | Notes |
| --- | --- | --- | --- |
| OpenAlex | works search, works by ID, referenced_works, cited_by | no key; polite pool with email gives higher limits, roughly 10 requests per second | abstracts come as inverted index; write the reconstruction once, test it |
| Semantic Scholar | paper search, paper details, references, citations, recommendations, embeddings | free key required; around 1 request per second with key | SPECTER embeddings on the paper endpoint; batch endpoint for up to 500 IDs |
| arXiv | query API, by ID | no key; 1 request every 3 seconds is the polite rate | newest preprints; results as Atom XML |
| PubMed E-utilities | esearch, efetch, elink | no key 3 per second; free key 10 per second | elink gives citation links inside PubMed |
| Crossref | works by DOI, works search | no key; polite pool with email | best DOI metadata and BibTeX-ready fields |
| Unpaywall | by DOI | no key; email required; 100k per day | best open-access PDF link per DOI |

Each client has a rate limiter, retries with backoff on 429 and 5xx, an on-disk cache keyed by URL so re-running a search costs nothing, and a cassette test.

**Day 9 to 11: model layer.**

1. Define the interface: chat with optional JSON schema, embed, rerank. Define a Pydantic result type with text, parsed JSON, token counts, latency, model name.
2. Ollama backend using its HTTP API, with JSON mode for chat and the embeddings endpoint. OpenAI-compatible backend for everything else.
3. Embedding backend for SPECTER2 via sentence-transformers, cached to disk by text hash.
4. Reranker backend: start with LLM pointwise scoring; leave a slot for a cross-encoder later.
5. Step registry: config maps step names to backend plus model. A step not in config falls back to the local default and logs a warning.
6. A stub backend for tests that returns canned responses from a fixture file.

**Day 12 to 14: run logging and finish.**

1. Run context manager: opens a run row, snapshots config, git hash, prompt versions; on exit records stats and duration. Every subcommand uses it.
2. The `doctor` command reports store version, row counts, last run per tool.
3. Write README quickstart: install, create config.local, run doctor.
4. Phase 0 checklist below.

### 5.3 Phase 0 checklist

- `doctor` passes on your machine with Postgres reachable, pgvector loaded, Ollama and one local model available
- All six clients return mapped records in tests from cassettes
- ID normalization tests cover at least 25 cases including the ugly ones
- Upsert never overwrites filled fields with empty ones (tested)
- One end-to-end smoke test: search OpenAlex for a phrase, upsert 10 papers, embed them, store embeddings, read them back
- Run rows are written with config snapshot and git hash
- Test suite runs offline in under 60 seconds

### 5.4 Common mistakes to avoid here

- Building a fancy CLI framework. Use a minimal argument parser; the tools are few.
- Adding a separate vector database or search engine. pgvector and Postgres full-text search cover both at your scale; a second store is a second thing to keep in sync.
- Storing embeddings as JSON or float arrays. Use the pgvector column with an HNSW index so similarity is one query, and keep model name and dimension beside it because SPECTER2 and the chunk model have different sizes.
- Hardcoding model names. Every model name comes from config so eval runs can be compared across models.

