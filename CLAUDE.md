# CLAUDE.md

Project: **Scholium**, a modular, local-first research assistant for one researcher. Seven command-line tools (find, read, plan, write, cite, figures, check) over one shared Postgres store, built in phases over about 30 weeks alongside coursework. Owner: Veerbhadra Mahant. Domain of the first real project: conditional diffusion models for medical image synthesis.

Read this file first in every session. The full plan is in `docs/plan/`. The current phase and what is done is in `docs/STATUS.md`. Never start work that belongs to a later phase than the one in STATUS.md.

## Where things are

| Path | What |
| --- | --- |
| docs/plan/00_Scholium_Full_Execution_Plan.md | The whole plan. Read sections 1 to 4 before any architectural decision. |
| docs/plan/01_Foundation_Phase0.md | Architecture, method, and the Phase 0 build. Authoritative for store schema, model layer, config, testing. |
| docs/plan/02 to 08 | One file per tool. Read the tool's file in full before touching its package. |
| docs/plan/09_Integration.md | Orchestrator, GitHub tracking, risks, appendix of APIs and libraries. |
| docs/STATUS.md | Current phase, checklist state, last eval scores. Update it at the end of every working session. |
| docs/adr/ | Architecture decision records. Add one whenever a decision in plan section 2 changes. |
| docs/research/ | The landscape survey that motivated the project. Background only. |
| prompts/ | Every model prompt as a versioned text file. Never inline a prompt in code. |
| eval/ | Fixed evaluation sets and scoring scripts per tool. |
| projects/ | User research projects (problem.md, seeds.txt, notes). User data, mostly gitignored. |

## Non-negotiable rules

1. **Store first.** Every tool reads its inputs from the Postgres store and writes its outputs back. No tool keeps private state on disk except caches. All SQL lives in `scholium/store/`; no SQL anywhere else.
2. **Retrieval over generation.** A model may summarize, rank, rewrite or score retrieved text. It may never invent a paper, a citation key, a number, a dataset name or a URL. Where generation is unavoidable (plan, critique) the output is marked as a proposal that the user approves.
3. **Citations are lookups.** In `write`, the model may only emit citation placeholders from a menu built from the store. Code substitutes and validates them. An unknown key is an error, never a warning.
4. **Evidence spans.** Every extracted or checked fact stores the verbatim span and page it came from, and code verifies the span exists in the source text.
5. **Local by default, API by exception.** One model interface. Every named step (find.expand, read.extract, plan.gap, ...) is routed by config. Default is Ollama. Never hardcode a model name.
6. **Human gates.** Tool N never triggers tool N+1 automatically before Phase 4. The user labels, approves or edits between tools.
7. **Evaluate before extending.** A tool gets no new features until it passes the pass criterion in its plan section. Eval sets are built before tuning, never after.
8. **Merge early.** A tool branch merges to main the day it writes valid store rows. No branch lives longer than 14 days. Never branch off another tool's branch.
9. **Free forever.** Only free APIs (OpenAlex, Semantic Scholar, arXiv, PubMed, Crossref, Unpaywall) and open-weight models by default. Paid dependencies are optional and switchable off.
10. **No autonomous experiments, no AI-detection scoring.** The suite reads results from MLflow or CSV; it does not run training. Quality is checked by claim-to-evidence audit, not by a detector.

## Stack (decided, do not relitigate without an ADR)

- Python 3.11 or newer, type hints everywhere, Pydantic models for every store record and every model-layer JSON output.
- PostgreSQL 16 or newer with pgvector, via Docker Compose. psycopg 3 plus SQLAlchemy Core (not the ORM). Alembic for every schema change. HNSW cosine index on embeddings; tsvector plus GIN on paper title and abstract; JSONB for channels, config snapshots and stats.
- Models: Ollama for local LLMs; any OpenAI-compatible endpoint for API models; SPECTER2 via sentence-transformers for paper embeddings; a small general embedding model for chunks.
- HTTP: httpx with tenacity retries, a per-client token-bucket rate limiter, an on-disk response cache keyed by URL.
- Tests: pytest; API cassettes (vcrpy or respx); a stub model backend returning fixture JSON; store tests against a throwaway Postgres (testcontainers) with per-test transaction rollback. The offline suite must run in under two minutes.
- Tooling: ruff for lint and format, pre-commit running ruff and the fast tests.
- CLI: one console entry point `scholium` with one subcommand per tool plus `doctor`. Minimal argument parser, no heavy CLI framework.

## Coding conventions

- No global state. Functions take a store handle and a config object.
- Every model call returns a typed object or raises. Never parse free text with regex when JSON mode is available.
- Every function that calls an external API accepts a client object so tests can inject a recorded one.
- Every subcommand runs inside the run context manager, which writes a run row with config snapshot, git hash, model names, prompt versions and stats.
- Prompts live in `prompts/<step>.v<N>.txt`. Changing a prompt means a new version file, never an edit in place.
- Upserts merge non-null fields and never overwrite a filled field with an empty one.
- Canonical paper ID: lowercase DOI, else arXiv ID without version, else PMID, else OpenAlex ID, else a hash of normalized title plus first author surname plus year.

## How to work in a session

1. Read `docs/STATUS.md`. Confirm the current phase and the next unchecked item.
2. Read the relevant `docs/plan/` file for the tool or phase being worked on.
3. Work on a branch named `tool/<name>` or `tool/<name>-<feature>` off main. Phase 0 commits go straight to main.
4. Write tests alongside the code, not after.
5. Before finishing: run ruff and the fast tests, run the tool's eval if it exists, update `docs/STATUS.md` and add one line to `CHANGELOG.md`.
6. If a decision in plan section 2 changes, add `docs/adr/NNNN-<slug>.md` stating the decision, the reason and what it replaces.

## Things to push back on

If the user asks for any of the following, say so and point at the rule, then do it only if they confirm: a web UI before Phase 3, a second vector store or search engine, a chat-style interface, autonomous experiment execution, an AI-text detector, skipping an eval set, letting a model insert a citation key that is not in the store, a long-lived branch, or starting a later phase before the current gate is green.

## Style for anything written for the user

Plain prose, short sentences, no em dashes, minimal formatting. Numbered lists for clarifying questions. No diagrams unless asked. No code in chat responses unless asked.
