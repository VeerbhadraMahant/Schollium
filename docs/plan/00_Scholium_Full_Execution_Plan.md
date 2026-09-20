---
title: "Scholium: Full Execution Plan"
author: "Veerbhadra Mahant"
date: "18 September 2026"
---

## 1. Purpose, scope and governing principles

The goal is a modular, local-first research assistant built as seven tools in one repository, each usable alone and later combined. The first working tool (Find) should exist within four weeks; the full suite is a two-semester effort alongside coursework.

### 1.1 What is being built

One repository, one shared paper store, one model layer, seven subcommands. Each tool reads from the store and writes back to it. A human review step sits between every tool and the next.

| # | Tool | One-line job | Primary input | Primary output |
| --- | --- | --- | --- | --- |
| 0 | Foundation | Store, API clients, model layer, config | none | working package on main |
| 1 | Find | Discover papers around a problem statement beyond keyword matching | problem statement, optional seeds | scored candidate papers |
| 2 | Read | Pull full text and extract structured facts per paper | labeled relevant papers | extraction records |
| 3 | Plan | Gap analysis, research questions, experiment plan, paper outline | extractions, problem statement | editable plan |
| 4 | Write | Draft LaTeX sections with store-only citations | plan, notes, results | draft sections |
| 5 | Cite | Verify every citation resolves and supports its sentence, export .bib | draft sections | verified .bib, issue list |
| 6 | Figures | Draft plotting scripts and diagram sources from results | result logs, model description | figure scripts |
| 7 | Check | Reviewer-style critique and claim-to-evidence audit | full draft | review report |

### 1.2 Why build instead of buy

The survey (September 2026) showed no free, local, ML-focused system that composes discovery, grounded writing and verification. Commercial tools are cloud only and per-seat priced. Open systems (PaperQA2, Agent Laboratory, AIDE) each cover one layer and do not share state. The value of building is one store with your relevance labels that every tool learns from.

### 1.3 Principles that decide every ambiguity

1. Store first. Every tool's input and output is a row in the shared Postgres store. No tool keeps private state. This is the rule that makes the final merge cheap.
2. Retrieval over generation. A model may summarize, rank, or rewrite retrieved text. It may never invent a paper, a citation key, a number or a dataset name. Where generation is unavoidable (plan, critique) the output is labeled as proposal and requires human approval.
3. Local by default, API by exception. Every model call goes through one interface. The default is a local model on the 24 GB card. An API key may be set per step, never globally.
4. Commands, not chat. Each tool is a command that takes explicit inputs and writes explicit outputs. No open-ended conversational interface. Chat interfaces are where research assistants become vague.
5. Human in the loop at every boundary. Tool N never triggers tool N plus 1 automatically until Phase 4. The person labels, approves or edits between them.
6. Merge early. A tool branch merges into main the day it writes valid rows to the store, even if rough. Long-lived branches are forbidden.
7. Evaluate before extending. Each tool has a small fixed evaluation set and a pass criterion. No feature work on a tool until it passes its criterion.
8. Free forever. Only free APIs (OpenAlex, Semantic Scholar, arXiv, PubMed, Crossref, Unpaywall) and open-weight models. Any paid dependency must be optional and switchable off.

### 1.4 Explicit non-goals

- No autonomous experiment execution. Experiments stay in your existing training code and MLflow. The suite reads results, it does not run training.
- No AI-detection scoring. Detectors have high false positive rates on technical and non-native English text and are trivially evaded. Quality is checked by claim-to-evidence audit, not by a detector.
- No web UI in the first two phases. Terminal plus a minimal local page for labeling only.
- No multi-user support. Single researcher, single machine.

### 1.5 Success criteria for the whole project

- Find: on a held-out set of 30 papers you already know are relevant, recall at least 24 (80 percent) without any of their titles or keywords in the query.
- Read: 90 percent of extraction fields judged correct on 20 hand-checked papers.
- Write plus Cite: zero citation keys in any generated draft that do not resolve to a store row with a DOI or arXiv ID.
- End to end: one real paper section of your honors work drafted, cited, figured and reviewed through the suite, with the review catching at least one real issue you had missed.

## 2. Overall architecture

A single Python package over one shared PostgreSQL store with pgvector, a thin API-client layer, one model interface, and one subpackage per tool. Nothing else is shared between tools; everything passes through the store. The store is the only coupling point, which is what keeps each tool usable alone and the final merge cheap.

### 2.1 Repository layout

| Path | Purpose | Owner phase |
| --- | --- | --- |
| pyproject.toml | Package metadata, single entry point command `scholium` | 0 |
| scholium/config.py | Loads one TOML config: paths, model per step, API keys, rate limits | 0 |
| scholium/store/ | Schema, migrations, typed access functions for every table | 0 |
| scholium/clients/ | One module per external API. Phase 0: openalex, semanticscholar, arxiv, pubmed, europepmc, crossref, unpaywall, dblp. Phase 1 (ADR 0002): openreview, core, springernature, biorxiv | 0 and 1 |
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

## 4. Timeline

Five phases over roughly 30 weeks, starting the week of 21 September 2026 and finishing around mid April 2027, at 8 to 12 hours per week. Find is usable by week 4, the writing chain by week 16, and the integrated pipeline by week 28.

### 4.1 Phase overview

| Phase | Weeks | Dates (approx.) | Deliverable | Gate to next phase |
| --- | --- | --- | --- | --- |
| 0 Foundation | 1 to 2 | 21 Sep to 4 Oct 2026 | Store, clients, model layer, config, tests on main | Phase 0 checklist green |
| 1 Discovery | 3 to 8 | 5 Oct to 15 Nov 2026 | Find and Read merged and evaluated | Find recall 80 percent; Read accuracy 90 percent |
| 2 Writing chain | 9 to 16 | 16 Nov 2026 to 10 Jan 2027 | Plan, Write, Cite merged | One real section drafted with 100 percent valid citations |
| 3 Presentation and review | 17 to 22 | 11 Jan to 21 Feb 2027 | Figures and Check merged | Planted-issue eval passed |
| 4 Integration | 23 to 28 | 22 Feb to 4 Apr 2027 | Orchestrator, end-to-end run, GitHub tracking | Full run on a real project |
| 5 Hardening | 29 to 30 | 5 Apr to 18 Apr 2027 | Docs, cleanup, optional public release | README quickstart works on a fresh machine |

Exam weeks and the internship start (a November 2026 target) are not modeled. Expect two to three slipped weeks; the end date is April, not March, for that reason.

### 4.2 Week-by-week plan

| Week | Dates | Work | Output |
| --- | --- | --- | --- |
| 1 | 21 Sep | Repo, package skeleton, docker compose for Postgres with pgvector, config loader, Alembic schema and migrations, paper ID normalization with tests | main boots, empty store created |
| 2 | 28 Sep | Clients for OpenAlex, Semantic Scholar, arXiv, PubMed, Crossref, Unpaywall with rate limiting and cassettes; model layer with Ollama backend; run logging | Phase 0 checklist green |
| 3 | 5 Oct | Find: project creation, query expansion, keyword channel across three sources, dedup, store writes | First candidates in the store |
| 4 | 12 Oct | Find: embedding channel (SPECTER2 local plus Semantic Scholar), fusion, local reranker, terminal review view | Find usable; first labels |
| 5 | 19 Oct | Find: citation snowballing from labels, caps, eval set of 30 held-out papers, scoring script | Recall measured |
| 6 | 26 Oct | Find: tune to reach 80 percent recall; PubMed noise filter; merge | Find done for Phase 1 |
| 7 | 2 Nov | Read: PDF acquisition via Unpaywall and arXiv, parsing, section splitting, chunk embeddings | Full text for relevant papers |
| 8 | 9 Nov | Read: extraction schema, JSON-mode extraction with evidence spans, eval on 20 papers, merge | Phase 1 gate |
| 9 | 16 Nov | Plan: gap matrix from extractions, prompts for gap analysis | First gap analysis |
| 10 | 23 Nov | Plan: research questions, experiment plan, outline; approval workflow; eval | Plan merged |
| 11 | 30 Nov | Write: section drafting from approved plan, store-only citation keys, LaTeX output | First drafted section |
| 12 | 7 Dec | Write: revision loop, style guide injection, eval on your 5 existing sections | Write merged |
| 13 | 14 Dec | Cite: key resolution against Crossref and OpenAlex, retraction check | Resolution working |
| 14 | 21 Dec | Cite: support scoring per citation sentence, .bib export, issue report | Cite merged |
| 15 | 28 Dec | Buffer week (holidays) | catch-up |
| 16 | 4 Jan | Phase 2 gate: draft one real section of the honors paper through Plan, Write, Cite | Phase 2 gate |
| 17 | 11 Jan | Figures: result ingestion from MLflow and CSV, plot spec schema | Result ingestion |
| 18 | 18 Jan | Figures: plotting script generation, style template, run-and-verify loop | Figures merged |
| 19 | 25 Jan | Figures: diagram source generation (TikZ or draw.io XML) from model description; eval | Diagrams working |
| 20 | 1 Feb | Check: review rubric, reviewer-simulation prompts | First review report |
| 21 | 8 Feb | Check: claim-to-evidence audit linking numbers to tables and figures; planted-issue eval | Check merged |
| 22 | 15 Feb | Phase 3 gate; buffer | Phase 3 gate |
| 23 | 22 Feb | Orchestrate: pipeline definition, approval gates, resume from any step | Pipeline runs manually |
| 24 | 1 Mar | Orchestrate: GitHub tracking (auto-commit of drafts and figures per run, run log in repo) | Repo-tracked runs |
| 25 | 8 Mar | End-to-end run on a second small project (not the honors work) to find coupling bugs | Bug list |
| 26 | 15 Mar | Fix coupling bugs; MLflow and W&B readers | Integration stable |
| 27 | 22 Mar | Buffer | catch-up |
| 28 | 29 Mar | Phase 4 gate: full run on the honors project | Phase 4 gate |
| 29 | 5 Apr | Docs, README quickstart, fresh-machine install test | Docs complete |
| 30 | 12 Apr | Cleanup, decide on public release, tag v1.0 | Done |

### 4.3 Checkpoints that must not be skipped

1. End of week 2: do not start Find without the store, ID rules and run logging. Retrofitting run logging later is the most common cause of unreproducible eval numbers.
2. End of week 6: Find must hit 80 percent recall before Read starts. If it does not, the corpus your whole suite reads from is wrong, and everything downstream inherits the gap.
3. End of week 16: one real section through Plan, Write and Cite with zero invalid citation keys. If any key is invented, stop and fix the constraint mechanism before any Phase 3 work.
4. End of week 28: a full run on the honors project. This is the only checkpoint that tests whether the suite helps you rather than just runs.

### 4.4 What to do if you fall behind

Drop in this order: Figures diagram generation (week 19), W&B reader (week 26), public release (week 30), Check's reviewer simulation (keep the claim-to-evidence audit). Never drop an eval set or a gate.
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
| Europe PMC | search, article by ID, full text XML, citations and references | no key; polite use | superset of PubMed; open-access full text as XML, which parses far better than PDF |
| DBLP | publication search, author search, venue listing | no key; polite rate | canonical computer science venue names and series; use it to make MICCAI, CVPR and NeurIPS filterable rather than string-matched |
Phase 1 adds four more clients on a `tool/find-sources` branch, each admitted only if the section 6.7 recall ablation shows it contributes: OpenReview (ML venue submissions and reviews before DOIs exist), CORE (open-access full text from institutional repositories when Unpaywall has no link), Springer Nature (free key, 100 requests per minute on the open access tier, and MICCAI is Springer LNCS), and bioRxiv with medRxiv as one client. IEEE Xplore, ResearchGate, Google Scholar, Scopus and Web of Science are rejected; see ADR 0002 for why.

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
- All eight Phase 0 clients return mapped records in tests from cassettes
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

## 6. Tool 1: Find (weeks 3 to 6)

Find turns a paragraph-length problem statement into a scored candidate list using three vocabulary-independent channels, then learns from your labels. Pass criterion: 80 percent recall on 30 held-out known-relevant papers.

### 6.1 Why three channels

Keyword search finds papers that share your words. Your field renames the same idea often: score-based generative model, DDPM, conditional diffusion, cross-modality synthesis, image-to-image translation, MR-to-CT. Each channel below fails differently, so their union covers what any single one misses.

| Channel | Finds | Misses | Cost |
| --- | --- | --- | --- |
| Query expansion plus keyword search | papers using any of 15 to 20 phrasings the model generates | papers using phrasings the model did not think of | cheap, one local model call plus API queries |
| Embedding similarity | papers about the same thing in any words | very new papers not yet in the embedding index, papers whose abstract is vague | cheap after first embedding |
| Citation snowballing | papers connected to your seeds regardless of words | papers in a disconnected cluster, very new papers with no citations | grows fast; must be capped |

### 6.2 Inputs

- A project folder with problem.md: one to three paragraphs in plain language describing what you are working on, what you want to know, and what is out of scope. Not a keyword list. This is the most important input and deserves an hour of writing.
- Optional seeds.txt: DOIs or arXiv IDs of papers you already know are relevant. Zero is acceptable; snowballing then waits for your first labels.
- Flags: year range (default 2015 to now), candidates per channel (default 300), snowball hops (default 1, max 2), similarity floor (default 0.55 cosine on SPECTER2, tune on eval), sources on or off per channel.

### 6.3 Pipeline, step by step

**Step 1: query expansion.** The local model receives the problem statement and produces a JSON list of 15 to 20 search phrasings grouped by intent: method names, task names, modality names, evaluation terms, adjacent subfields. The prompt explicitly asks for older terminology and for terms used in clinical venues versus ML venues. Store the expansions in the run stats so you can inspect what the model thought your topic was.

**Step 2: keyword channel.** Each phrasing is searched against OpenAlex, arXiv, PubMed, Europe PMC and DBLP with the year filter, and against the Phase 1 sources in ADR 0002 once they are admitted. Results are mapped to store records and upserted. Each candidate remembers which phrasing found it. Cap per phrasing per source at 50 to keep the first run under a few minutes.

**Step 3: embedding channel.** Embed the problem statement with SPECTER2 (adapter for proximity). Query Semantic Scholar's search with the top phrasings and fetch SPECTER embeddings for results in batches of 500. Also embed everything already in the store that lacks a vector. Compute cosine similarity to the problem statement and keep everything above the floor. In later runs, also compute similarity to the centroid of your relevant-labeled papers; that centroid is a better query than the problem statement once you have 20 or more labels.

**Step 4: snowball channel.** For each seed and each relevant-labeled paper, fetch references and citations from OpenAlex and Semantic Scholar. Record citation edges. Score each discovered paper by how many seeds it is connected to. Cap by keeping the top 500 by connection count, then by similarity. Two hops only when the one-hop set is under 200.

**Step 5: dedup.** Canonical ID first. Then normalized title (lowercase, strip punctuation and LaTeX, collapse whitespace) plus year within 1. arXiv preprint and journal version merge into one row keeping the DOI as canonical and the arXiv ID as an alias. Log every merge so you can audit false merges.

**Step 6: fusion.** Score equals a weighted sum of: number of channels that found it (strongest signal), max similarity, snowball connection count normalized, and a small recency bonus. Start with weights 3, 2, 1, 0.5 and tune on the eval set. Candidates already labeled irrelevant are excluded; already relevant are excluded from the output but still used as seeds.

**Step 7: rerank.** The top 200 by fusion go to the local model one at a time with the problem statement, title and abstract, asking for a score 1 to 5 and a one-sentence reason. JSON mode. Store both. The reason is what makes the review view fast to scan.

**Step 8: write and review.** Candidate rows are written with all scores and channels. The review view lists candidates sorted by rerank then fusion, shows title, year, venue, the reason, the channels, and takes one keystroke per paper: relevant, irrelevant, maybe, open PDF link, skip. Labels write immediately.

### 6.4 The review view

Start as a terminal table with keyboard navigation. Upgrade to a single-page local web view only if you find yourself labeling more than 100 papers per session. The review view is the most-used surface in the whole suite; keep it under 200 milliseconds per action.

### 6.5 Learning from labels

- Every run: irrelevant labels are excluded, relevant labels expand snowballing and shift the embedding centroid.
- After 50 labels: train a logistic regression on SPECTER2 vectors as a second reranker. Compare against the LLM reranker on the eval set. Keep whichever wins, or average them.
- After 200 labels: retire the problem-statement query entirely in favor of the centroid plus classifier. This is where the tool becomes yours rather than generic.

### 6.6 PubMed noise

PubMed returns many clinical papers that mention diffusion models in passing. Mitigate in order: require the phrasing to appear in title or abstract rather than MeSH terms, lower PubMed's cap to 20 per phrasing, and add a venue-type feature to fusion so purely clinical journals get a small penalty unless snowballing also finds them. Evaluate each mitigation on recall before keeping it; do not filter blind.

### 6.7 Evaluation

1. Build the eval set before tuning: 30 papers you already know are relevant. Split into 10 seeds and 20 held-out. The held-out titles and their exact keywords must not appear in problem.md.
2. Run Find with seeds only. Metric: how many of the 20 held-out appear in the top 200 candidates. Target 16 of 20 (80 percent). Also record recall at 50 and at 100 to see how much the reranker helps.
3. Ablate: each channel off in turn. If a channel adds under 2 percent recall on your topic, keep it but lower its default cap.
4. Repeat with zero seeds to measure bootstrap-from-statement performance. Expect lower; record it.
5. Precision spot check: label the top 50 and count relevant. Above 30 percent at top 50 is fine for a recall tool.

### 6.8 Build order within the branch

1. Day 1: project create command, problem.md loading, expansion prompt, expansion stored in run stats.
2. Day 2: keyword channel over OpenAlex only, dedup, store writes. Ship the vertical slice, merge.
3. Day 3 to 4: arXiv and PubMed sources, embedding channel, fusion.
4. Day 5: reranker, review view, labels.
5. Day 6 to 7: snowballing, eval set, scoring script.
6. Days 8 to 12: tuning, PubMed noise, docs.

### 6.9 Known failure modes

- Semantic Scholar rate limits stall the embedding channel. Mitigation: batch endpoint, disk cache, and a local SPECTER2 fallback that embeds abstracts fetched from OpenAlex.
- The expansion model drifts off topic (for example into general GANs). Mitigation: include two or three negative phrasings in the prompt and exclude candidates matching only those.
- Snowballing explodes on a highly cited seed. Mitigation: per-seed cap of 300 citations, prefer references over citations for classic papers.
- False title merges between a workshop and conference version with different content. Acceptable; log and let the label step catch it.
## 7. Tool 2: Read and Synthesize (weeks 7 to 8)

Read fetches full text for relevant-labeled papers and extracts a fixed set of structured fields, each with the exact evidence span it came from. Pass criterion: 90 percent field accuracy on 20 hand-checked papers.

### 7.1 Why this tool exists

Plan, Write and Check all need to know what each paper actually did, not what its abstract claims. Abstracts overstate. Method sections, tables and limitation paragraphs are where the real facts live. Extracting them once into a fixed schema means every downstream tool reasons over the same verified facts, and every claim it makes can be traced to a page.

### 7.2 Inputs

- All papers labeled relevant for the project (and optionally maybe).
- Flags: force re-extract, fields subset, max pages, model step override.

### 7.3 Full-text acquisition

1. Ask Unpaywall by DOI for the best open-access PDF URL. Then arXiv by ID. Then the OpenAlex oa_url. Then PubMed Central by PMID.
2. Download to data/pdfs/{paper_id}.pdf with a checksum. Never re-download a file whose checksum exists.
3. Papers with no open PDF are flagged in the store. You add them by hand from your institution's access into the same folder with the same name, and Read picks them up next run. Do not attempt paywall workarounds in the tool.
4. Also accept a Zotero storage directory as a source: match PDFs to store rows by DOI in the PDF metadata or by title fuzzy match, and log matches for audit.

### 7.4 Parsing

Use a layout-aware parser (PyMuPDF for speed, with a fallback to a GROBID container if you want reference lists and section labels parsed properly). Output per paper: ordered sections with headings, paragraphs with page numbers, tables as text grids, figure captions, and the reference list. Store chunks of about 400 tokens with section name and page, plus a SPECTER2 or general embedding per chunk for retrieval within a paper.

Two-column ML papers and scanned medical journals break naive parsers. Spend the parsing day on a test set of 10 PDFs spanning arXiv, IEEE, Springer and a MICCAI-style template, and fix ordering bugs before extraction.

### 7.5 Extraction schema

Fixed fields, each with value, evidence span, page, confidence, and the model that filled it. Unknown is a valid value and is better than a guess.

| Field | What to capture | Typical source section |
| --- | --- | --- |
| problem | the task in one sentence | intro |
| method_family | e.g. DDPM, score SDE, latent diffusion, GAN, flow | method |
| conditioning | what conditions the model and how (concat, cross-attention, classifier-free guidance, ControlNet-style) | method |
| modalities | input and output modalities (MR T1, CT, PET, mask, text) | method, data |
| datasets | names, sizes, public or private, splits | data, experiments |
| baselines | methods compared against | experiments |
| metrics | names and reported values for the main result | results tables |
| compute | GPUs, training time, if stated | experiments or appendix |
| privacy_aspect | any privacy, federated, DP or synthetic-data-release angle | anywhere |
| limitations | authors' own stated limitations | discussion |
| claimed_novelty | what the authors say is new | intro, conclusion |
| code_available | URL if any | footnotes, abstract |

The schema is a config file, not code, so you can add fields (for example anatomy, resolution, 2D versus 3D) without touching the extractor. Any field added later is back-filled by a re-extract run on all papers.

### 7.6 Extraction procedure

1. For each field, retrieve the top 6 chunks by embedding similarity to a field-specific query, plus any chunk from the field's typical section.
2. Send those chunks with page numbers to the model in JSON mode, asking for value, the verbatim supporting span, its page, and a confidence 0 to 1. The prompt forbids answering from outside the provided chunks.
3. Verify the returned span actually occurs in the chunk text. If not, mark confidence 0 and flag. This single check catches most hallucinated extractions.
4. Store one extraction row per field. Re-runs create a new version; old versions are kept.
5. Produce a per-paper markdown summary card from the extraction rows, saved under the project folder, for your own reading.

### 7.7 Synthesis outputs

After extraction, produce two project-level artifacts that Plan will read:

- A comparison table across all relevant papers with one row per paper and one column per schema field. Written as CSV and markdown.
- A vocabulary map: every distinct term found in method_family, conditioning and modalities, with counts. This feeds back into Find's query expansion prompt as known-vocabulary context in later runs.

### 7.8 Evaluation

1. Choose 20 relevant papers. Fill the schema by hand for each. This takes a weekend and is the most valuable dataset in the project.
2. Run extraction. Score each field: exact match for categorical fields, judged match for free text. Target 90 percent overall, 95 percent for datasets and metrics since those feed Write directly.
3. Check span validity: 100 percent of stored spans must occur in the source. Any failure is a bug, not a tuning issue.
4. Compare the 8B and 14B local models. Move only the fields that fail to a larger or API model.

### 7.9 Build order

1. Day 1: PDF acquisition and storage, checksum, manual-add folder.
2. Day 2: parsing, chunking, chunk embeddings on the 10-PDF test set.
3. Day 3: schema config, single-field extraction with span verification. Merge the vertical slice.
4. Day 4: all fields, versioning, summary cards.
5. Day 5: comparison table, vocabulary map, eval set and scoring.
6. Days 6 to 7: tuning, model comparison, docs.

### 7.10 Known failure modes

- Numbers read from the wrong table row. Mitigation: tables are passed as grids with row and column headers, and the prompt asks for the header labels alongside the value.
- Supplementary material holds the real dataset details. Mitigation: if arXiv, fetch the full source and include appendix text; otherwise flag as partial.
- Long papers exceed context. Mitigation: retrieval per field, never whole-paper prompts.
- Confident wrong answers on fields the paper does not address. Mitigation: unknown is explicitly allowed and rewarded in the prompt; span verification catches the rest.

## 8. Tool 3: Plan (weeks 9 to 10)

Plan turns the extraction table into a gap analysis, candidate research questions, an experiment plan and a paper outline, all marked as proposals until you approve or edit them. Pass criterion: on 3 problem statements, it surfaces at least 2 of the 3 major gaps you identified yourself.

### 8.1 Why it must stay a proposer

Audits of autonomous research systems found they routinely label established ideas as novel and choose experiments that are easy rather than informative. A local model will be worse at this than a frontier one. So Plan never decides. It computes what can be computed from the extraction table (coverage, contradictions, frequency), proposes what requires judgment, and records your edits as the truth. Your approved plan, not the model's, is what Write reads.

### 8.2 Inputs

- The extraction comparison table for the project.
- problem.md.
- Optional constraints file: available datasets, compute budget (GPU hours), deadline, target venue and its page limit.
- Your notes folder, if any, as additional context.

### 8.3 Stage 1: computed gap matrix (no model)

Before any prompt, compute facts from the table:

- Coverage counts: how many papers per method_family, per conditioning type, per modality pair, per dataset, per metric.
- Empty cells of the matrix: modality pairs or conditioning types with zero or one paper.
- Contradictions: papers reporting the same metric on the same dataset with values differing by more than a threshold, or papers whose limitations sections name a problem another paper claims to solve.
- Recency: which methods appear only before 2023, which only after.
- Privacy angle coverage: how many papers address it at all, since it is central to your honors topic.

This stage is pure code and is where most of the real insight comes from. The model's job later is to explain and prioritize, not to discover.

### 8.4 Stage 2: gap analysis (model)

The model receives the computed facts, the problem statement and the constraints, and returns JSON: a ranked list of gaps, each with the evidence cells it rests on (paper IDs and fields), why it matters, how hard it is, and what would be needed to address it. The prompt requires every gap to cite at least two extraction rows by paper ID and forbids gaps not grounded in the table. Gaps citing nonexistent paper IDs are dropped by code.

### 8.5 Stage 3: research questions and experiment plan (model plus you)

For each of the top gaps the model proposes: a research question, a testable hypothesis, the minimal experiment that would falsify it, required datasets (only from those in the table or your constraints file), baselines (only from the baselines column), metrics (only from the metrics column), and an estimate of GPU hours against your budget. It also produces a risk note: what would make the result uninteresting even if it works.

You then edit in a plain markdown file per plan version. The tool re-imports your edited file and marks the plan approved. The diff between proposed and approved is stored; over time it shows you what the model gets wrong about your field.

### 8.6 Stage 4: paper outline

From the approved plan and the target venue, produce a section-by-section outline: for each section, its purpose, the claims it must make, the extraction rows and figures it will draw on, and a target length. This outline is the contract Write follows; Write may not add claims that are not in the outline.

### 8.7 Model choice

Stages 2 and 3 are the strongest case in the suite for an API model. Run both a 14B to 32B local model and a frontier model on the eval set and compare which gaps they find. Keep local as default if the difference is small; document the choice in an ADR.

### 8.8 Evaluation

1. Write your own gap analysis for 3 problem statements before running the tool, sealed in eval/.
2. Run Plan. For each statement, count how many of your top 3 gaps appear in the tool's top 5.
3. Count hallucinated gaps: gaps whose cited rows do not support them. Target zero.
4. Ask your honors supervisor to rate the proposed experiment plans for one statement on a 1 to 5 scale for sensibleness. Below 3 means the plan stage needs a better model or better constraints.

### 8.9 Build order

1. Day 1: computed gap matrix and a printed report. Merge.
2. Day 2: gap analysis prompt with grounding validation.
3. Day 3: research questions and experiment plan, constraints file.
4. Day 4: edit-import-approve loop and diff storage.
5. Day 5: outline generation, eval, docs.

### 8.10 Known failure modes

- Generic gaps ("more data needed", "3D is underexplored"). Mitigation: require quantitative grounding and reject gaps whose evidence is fewer than two rows.
- Experiment plans that ignore compute budget. Mitigation: the GPU-hour estimate is checked by code against the constraints file and over-budget plans are flagged before you see them.
- Overconfident novelty. Mitigation: for every proposed research question, Find runs a quick embedding search with that question as the query and lists the 5 closest existing papers under it. If one of them already does it, you see that immediately.

## 9. Tool 4: Write (weeks 11 to 12)

Write drafts one LaTeX section at a time from the approved outline, your notes and your results, and can only cite keys that exist in the store. Pass criterion: 100 percent valid citation keys and no statement contradicting an extraction row, on 5 sections you already wrote.

### 9.1 The one rule that matters

Citations are lookups, never generations. Before drafting, Write assembles a citation menu: every relevant paper's key, title, one-line summary from extractions, and the claims it supports. The model may only use keys from that menu, inserted as a placeholder token. Code replaces tokens with real \cite commands and rejects any token not in the menu. A hallucinated reference is therefore a parse error, not something you have to notice.

### 9.2 Inputs

- Approved outline for the target section, with its claims list.
- Extraction rows for the papers assigned to that section.
- Your notes file for the section, if any (bullet points, half-sentences, what you want to say).
- Results: tables exported from MLflow or CSV, already registered in the store by Figures or by a simple import command.
- A style file: venue, tense conventions, terminology to use and avoid, sentence length target, first-person policy.
- Optional: an existing draft of the section to revise rather than write fresh.

### 9.3 Drafting procedure

1. Build the citation menu for the section (section 9.1).
2. Build the fact sheet: every extraction row and every result number the section is allowed to use, each with an ID.
3. Prompt the model with outline, claims, fact sheet, citation menu, style file and notes. Ask for LaTeX for this section only, with citation placeholders and fact placeholders (every number must be a fact ID, never a literal).
4. Code substitutes placeholders. Unknown citation or fact IDs fail the draft with a list of offenders. The model is re-prompted with the offender list once; if it fails again, the draft is saved with the offenders marked in red comments for you.
5. Store the draft version with its cite keys and fact IDs. Write the .tex file into the project's paper folder under sections/.
6. Print a coverage report: which outline claims were made, which were skipped, which facts were unused.

### 9.4 Revision loop

A revise command takes the current section, your inline comments (as LaTeX comments starting with a marker), and produces a new version addressing each comment, again under the citation and fact constraints. Comments and the diff are stored. You should never lose a version.

### 9.5 What Write deliberately does not do

- It does not write the whole paper at once. Section by section keeps context small enough for a 14B local model and keeps you in control.
- It does not invent related-work groupings. The related-work section is drafted from the Plan gap matrix's method-family groups, one paragraph per group, using only papers in that group.
- It does not paraphrase extracted evidence spans verbatim. The prompt instructs it to state the fact in its own words and cite; direct quotes are not used in ML papers.
- It does not touch the results numbers. They come only from fact IDs.

### 9.6 Style control

The style file is short and specific. Example entries: use "conditional diffusion model" not "conditioned diffusion model"; past tense for what was done, present for what is shown; no sentences over 30 words; no hedge stacking; no claim of novelty without a citation to what came before. Run a lightweight post-check that flags banned words, sentence length violations and missing citations on sentences containing "previous work" or "prior".

### 9.7 Local versus API

First drafts on the 14B local model are acceptable and free. For a submission-quality pass, route write.section to a frontier model for one revision cycle. Keep both outputs; compare on the eval set. The citation constraint holds regardless of model, which is the point.

### 9.8 Evaluation

1. Take 5 sections you have already written for coursework or the honors program. Build their outlines and fact sheets by hand.
2. Run Write. Check: all keys valid (must be 100 percent), all numbers traceable to fact IDs (100 percent), claims coverage above 80 percent.
3. Read each draft against the extraction rows for contradictions. Target zero.
4. Blind comparison: shuffle your original and the tool's draft, have a labmate say which reads better and why. This is not a pass criterion, it is calibration for how much editing to expect.

### 9.9 Build order

1. Day 1: citation menu, fact sheet, placeholder grammar and validator. Merge with a stub prompt.
2. Day 2: drafting prompt, substitution, coverage report.
3. Day 3: revision loop, version storage.
4. Day 4: style file and post-check.
5. Day 5: eval, related-work grouping, docs.

### 9.10 Known failure modes

- The model cites a real key for a claim that paper does not make. This is not caught here; it is Cite's job (section 10).
- Repetitive phrasing across sections. Mitigation: pass the previous section's first sentences as "do not repeat" context.
- LaTeX that does not compile. Mitigation: compile each section inside a minimal wrapper document after drafting; failures are reported with the line.

## 10. Tool 5: Cite (weeks 13 to 14)

Cite verifies that every citation in a draft resolves to a real paper, is not retracted, and actually supports the sentence it is attached to, then exports a clean .bib. Pass criterion: 90 percent precision and recall on 100 citation sentences of which 20 are deliberately wrong.

### 10.1 Why a separate tool when Write already constrains keys

Write guarantees the key exists. It does not guarantee the paper says what the sentence claims. Miscitation of real papers is the dominant citation error in human-written ML papers too. Cite also runs on drafts you wrote by hand, on your supervisor's drafts, and on any .tex plus .bib pair, which makes it the most reusable tool in the suite.

### 10.2 Inputs

- A .tex file or a store draft ID, plus its .bib if external.
- Flags: support-check on or off (it is the expensive step), strictness threshold, format for the issue report.

### 10.3 Stage 1: resolution

1. Parse every \cite variant and every bib entry.
2. For each key: find the store row; if none, look up by DOI, then title plus first author plus year against Crossref and OpenAlex, then arXiv. Create a store row on success.
3. Compare bib fields to the authoritative record: title, authors, year, venue. Flag mismatches above a small edit distance. Wrong year and wrong venue are the common ones.
4. Check retraction status via Crossref's retraction metadata and OpenAlex's is_retracted flag. Flag any retracted paper as an error, not a warning.
5. Prefer the published version over the arXiv preprint when both exist, and flag preprint citations that have a published version.

### 10.4 Stage 2: support scoring

1. Extract each citing sentence with one sentence of context on either side.
2. For each cited paper, retrieve the top 5 chunks from Read's chunk store by similarity to the citing sentence. If the paper was never read (no full text), fall back to the abstract and mark the check as abstract-only.
3. Ask the model in JSON mode: does the retrieved text support, partially support, not address, or contradict the claim in the citing sentence. Require a verbatim supporting or contradicting span and verify it exists in the chunk.
4. Store one cite_check row per (sentence, key) pair with the verdict, span and page.
5. Aggregate: any contradict is an error; not addressed is a warning; partial is a note.

### 10.5 Stage 3: report and export

- Issue report as markdown grouped by severity, each with the sentence, the key, the verdict and the evidence span, so you can fix in minutes.
- Clean .bib generated from authoritative records with stable keys (Better BibTeX style: authorYearFirstword). Never rewrite keys already used in the .tex; add an alias map instead.
- Optional: a Zotero export of the whole project bibliography via Zotero's local API so your library stays in sync.

### 10.6 Evaluation

1. Build the eval set: 80 correct citation sentences from your own drafts and from relevant papers, plus 20 deliberately wrong ones: 5 swapped keys, 5 wrong year or venue, 5 claims the paper does not make, 5 claims the paper contradicts.
2. Run Cite. Precision and recall on flagged items, target 90 percent each. Resolution errors should be caught at 100 percent; support errors are where the 90 percent target bites.
3. Compare abstract-only versus full-text support checking to see how much Read's full text matters. Expect a large gap; this is the argument for reading everything you cite.

### 10.7 Build order

1. Day 1: parsing, key resolution, field comparison, retraction check. Merge.
2. Day 2: support scoring over chunks.
3. Day 3: report and .bib export.
4. Day 4: eval set, scoring, tuning of the threshold.
5. Day 5: Zotero sync, docs.

### 10.8 Known failure modes

- A citing sentence makes several claims and the paper supports one. Mitigation: the prompt asks the model to split claims and verdict each; the report shows per-claim.
- Survey papers cited for a specific finding they only summarize. Mitigation: flag citations to papers whose extraction method_family is survey with a note to cite the primary source.
- Slow on long drafts. Mitigation: cache verdicts by (sentence hash, key); only changed sentences are rechecked on revision.

## 11. Tool 6: Figures (weeks 17 to 19)

Figures ingests your experiment results, generates plotting scripts from a declarative figure spec, runs them, and checks the output against the spec. It also drafts architecture diagram source from a textual model description. Pass criterion: 5 of 5 result tables produce a running script whose figure matches its spec.

### 11.1 Scope decision

The tool writes first drafts of plotting code and diagram source. You own the visual style, and the tool never edits a figure you have marked final. Aiming higher ("AI makes my figures") produces figures reviewers distrust. Aiming here saves the boring 80 percent and leaves you the judgment.

### 11.2 Inputs

- Results: MLflow runs (via its Python client, read only), W&B exports, or CSV files. An import command registers each as a result table in the store with column types.
- A figure spec per figure, written by you or proposed by Plan's outline: figure type (line, bar, box, image grid, qualitative comparison), x and y columns, grouping, error representation, axis labels with units, size in the venue's column width, and the claim the figure supports.
- A style template: one matplotlib style file for the project, plus a color palette that is colorblind-safe and prints in grayscale.

### 11.3 Plot generation procedure

1. Validate the spec against the result table: columns exist, types match, grouping cardinality is sane (under 8 series).
2. Prompt the model with the spec, a 10-row sample of the data, the style template and a fixed skeleton. Ask for a complete script that reads the registered table by ID, never a hardcoded path, and saves a PDF and a PNG at the spec's size.
3. Run the script in a subprocess with a timeout. On error, re-prompt once with the traceback.
4. Verify the output: file exists, dimensions match, and a vision-capable local model (or a simple image check) confirms the axis labels and legend entries match the spec. Mismatches are reported, not silently accepted.
5. Store the figure row with script path, source table, spec hash and status. Any change to the source table marks dependent figures stale.

### 11.4 Image grids and qualitative results

Medical image synthesis papers live on qualitative grids: input, ground truth, methods side by side, with difference maps. Support a grid spec type: rows are cases, columns are methods, with optional difference-map column and a windowing setting per modality. The script generator handles consistent normalization and cropping; you pick the cases.

### 11.5 Diagrams

Given a structured description of the model (blocks, inputs, outputs, connections, conditioning path), generate TikZ source, and as an alternative draw.io XML you can polish by hand. Keep this simple: box-and-arrow with labeled edges. Anything prettier is faster to draw yourself. Evaluate by compiling the TikZ and eyeballing. This is the first item to drop if behind schedule (section 4.4).

### 11.6 Linking to Write and Check

Each figure spec records the claim it supports. Write can reference figures by name in a section, and Check uses the claim link to verify that the text describing a figure matches the numbers in its source table.

### 11.7 Evaluation

1. Take 5 result tables from your honors experiments (or synthetic ones with the same shape).
2. Write 5 specs. Run Figures. All 5 scripts must run and pass the output check.
3. Modify one source table and confirm the dependent figure is marked stale.
4. Compile 3 diagram descriptions and judge whether you would start from the output or from scratch.

### 11.8 Build order

1. Day 1: result import from CSV and MLflow, table registry. Merge.
2. Day 2: spec schema, validation, style template.
3. Day 3: script generation, run, retry.
4. Day 4: output verification, staleness tracking.
5. Day 5: image grid spec type.
6. Days 6 to 7: diagrams, eval, docs.

### 11.9 Known failure modes

- Scripts that work on the 10-row sample and fail on the full table (NaNs, mixed types). Mitigation: the run step uses the full table; the sample is only for prompting.
- Plot type chosen badly for the data. Mitigation: the spec is written by you; the tool does not choose the type.
- Windowing and normalization differences between methods in image grids that make one method look better. Mitigation: one shared normalization per row, stated in the caption, enforced by the script skeleton.

## 12. Tool 7: Check (weeks 20 to 21)

Check audits a full draft on two axes: a mechanical claim-to-evidence audit that traces every number and claim to a table, figure, extraction or citation, and a reviewer-simulation critique against the target venue's review form. Pass criterion: all planted issues found on 3 test drafts.

### 12.1 What it is not

It is not an AI-text detector. Detectors score technical and non-native English prose as machine-written at high rates and are defeated by light edits, so a score would mislead you either way. If a venue has an AI-use policy, comply through disclosure and through the audit below, which is the thing that actually protects your credibility.

### 12.2 Inputs

- The full draft (all sections from Write or a .tex file), its .bib, the figure registry, the result tables, and the extraction table.
- The venue's review form or a default rubric (clarity, novelty, soundness, reproducibility, significance).

### 12.3 Stage 1: claim-to-evidence audit (mostly code)

1. Extract every sentence containing a number, a comparative (better, outperforms, improves, state of the art), or a citation.
2. For numeric sentences: match the number against the result tables and figure sources. Exact match passes; a rounding-consistent match passes with a note; no match is an error.
3. For comparative sentences: identify the compared entities and check that a table or figure contains both and that the direction is correct. A claim of improvement with no supporting row is an error.
4. For cited sentences: reuse Cite's verdicts; any contradict or not-addressed verdict is surfaced here again.
5. For novelty claims ("first", "novel", "to our knowledge"): run Find's embedding search on the sentence and list the 5 closest papers with similarity. Above a threshold, flag for your judgment.
6. Consistency: numbers repeated across abstract, results and conclusion must agree. Method details in the method section must match the extraction of your own paper (run Read on your own draft to get that; this catches drift between what you did and what you wrote).

### 12.4 Stage 2: reviewer simulation (model)

Prompt the model three times with different reviewer personas (a methods-focused reviewer, a clinical or application reviewer, a reproducibility reviewer), each given the rubric, the draft, and the Stage 1 findings. Each returns JSON: scores per criterion, a list of weaknesses each anchored to a section and quoted sentence, questions for the authors, and requested experiments. Code merges the three, deduplicates weaknesses by anchor, and ranks by how many reviewers raised them. Anchored weaknesses are kept; unanchored generic complaints are dropped.

### 12.5 Stage 3: reproducibility checklist

A fixed checklist filled by code where possible and by the model where not: datasets named with versions and splits, preprocessing stated, hyperparameters listed, seeds and number of runs, compute stated, code link present, evaluation metric definitions cited. Each item is satisfied, missing or partial, with the section it was found in.

### 12.6 Report

One markdown report per draft version: errors first, then warnings, then reviewer weaknesses ranked, then the checklist. Each item has a section anchor and the quoted sentence so fixing is a search, not a hunt. Stored as review rows and written to the project folder.

### 12.7 Evaluation

1. Take 3 drafts (your own or the eval sections). Plant 6 issues in each: 2 wrong numbers, 1 unsupported comparative, 1 miscitation, 1 novelty overclaim, 1 missing reproducibility item.
2. Run Check. All 18 planted issues must be found. False positives are counted and should stay under 10 per draft.
3. Separately, run Check on a real draft and note how many of its top 10 reviewer weaknesses you agree with. Under 5 means the personas or rubric need work.

### 12.8 Build order

1. Day 1: sentence extraction and numeric matching. Merge.
2. Day 2: comparative and consistency checks, Cite integration.
3. Day 3: novelty search, reviewer personas.
4. Day 4: reproducibility checklist, report.
5. Day 5: eval with planted issues, docs.

### 12.9 Known failure modes

- Numbers in text are legitimately derived (percent improvement computed from two table cells). Mitigation: allow simple derivations (difference, ratio, percent change) between any two matched cells.
- Reviewer personas produce polite non-findings. Mitigation: require each weakness to quote a sentence and propose a concrete fix; unanchored items are dropped by code.
- The model scores the paper it helped write generously. Mitigation: for the final pass, route check.review to a different model than write.section.

## 13. Integration (weeks 23 to 28)

Integration adds a thin orchestrator that runs the seven tools as a resumable pipeline with approval gates, and a tracking layer that commits every run's outputs to the project's git repository. Pass criterion: one full run on the honors project, from problem statement to reviewed draft, with every gate exercised.

### 13.1 Why the orchestrator is thin

Because every tool already reads and writes the store, the orchestrator only needs to know the order, the gates, and how to resume. It holds no logic of its own. If the orchestrator ever grows a prompt, that prompt belongs in a tool.

### 13.2 Pipeline definition

A pipeline file per project lists stages in order, each with: the tool and its flags, the gate type (auto, approve, edit), and the condition to skip (for example skip Read if no new relevant labels since last run).

| Stage | Tool | Gate | What you do at the gate |
| --- | --- | --- | --- |
| 1 | Find | edit | label candidates in the review view |
| 2 | Read | auto | nothing; runs on new relevant labels |
| 3 | Plan | edit | edit and approve the plan file |
| 4 | Write (per section) | approve | read each section, add revision comments or approve |
| 5 | Cite | auto | nothing; results feed Check |
| 6 | Figures | approve | mark figures final or edit specs |
| 7 | Check | approve | read the report, decide what to fix |

The runner records the pipeline state in the store: current stage, waiting-for-gate, last error. Resume from any stage. Re-running an earlier stage marks later stages stale but does not delete their outputs.

### 13.3 Implementation choice

Start with a plain Python state machine over the store. It is under 300 lines and fully testable. Move to LangGraph only if you later need parallel branches, streaming, or a UI, and only after the plain version has run end to end at least three times. Adopting a framework before the plain version works adds a dependency without adding understanding.

### 13.4 GitHub tracking

The research project folder is its own git repository, separate from the suite's repository. Tracking rules:

1. After every stage, the runner commits the project folder with a message naming the tool, run ID, and stats. Drafts, figures, plan versions, review reports and the exported .bib are all files, so the history is human-readable.
2. The database is not committed. A daily export of the project's tables to JSONL (plus a weekly pg_dump kept outside git) is committed, so the history of labels and extractions is recoverable and diffable.
3. PDFs are not committed. The paper table's export records where each came from.
4. Optional: push to a private GitHub repository via the GitHub CLI; open a pull request per paper section so revision comments live on the PR. This is a convenience, not a dependency.
5. Experiment tracking stays in MLflow. Figures reads run IDs; the export records which MLflow run each figure came from, so a figure can always be traced to a training run and a commit.

### 13.5 Result readers

MLflow first (local server or file store), then W&B via its export API if you use it. Both produce the same result-table shape in the store. Keep them read only.

### 13.6 The second-project shakedown (week 25)

Before the honors run, run the whole pipeline on a small unrelated topic with 10 seeds. The purpose is to surface coupling bugs: a Plan field Write expects but Read does not fill, a figure name Check cannot resolve, a stale flag that never clears. Fix these on main before touching the honors project. Expect a day of bugs.

### 13.7 End-to-end run on the honors project (week 28)

1. Fresh project, real problem statement, your real seeds.
2. Label at least 100 candidates. Read them all.
3. Approve a plan for one section of your actual paper (related work is the natural first section).
4. Draft, cite-check, add one figure, run Check.
5. Write a one-page retrospective: what the suite saved, what it got wrong, what you would drop. This retrospective decides Phase 5 scope.

### 13.8 Build order

1. Week 23: pipeline file, state machine, gates, resume. Merge.
2. Week 24: git tracking, JSONL export, optional PR flow.
3. Week 25: shakedown run, bug list.
4. Week 26: fixes, MLflow and W&B readers.
5. Week 27: buffer.
6. Week 28: honors run and retrospective.

## 14. Risks, failure modes and mitigations

The three risks most likely to sink the project are scope creep in Find, skipping evaluation sets to save a weekend, and letting a model output pass a gate without your reading it. Everything else is recoverable.

| Risk | Likelihood | Impact | Early signal | Mitigation |
| --- | --- | --- | --- | --- |
| Scope creep in Find (web UI, more sources, fancy ranking) delays everything | high | high | week 6 passes with no Read work started | hard stop at 80 percent recall; new Find features only after Phase 2 |
| Eval sets skipped or built after tuning | high | high | a tool merges without an eval/ folder | definition of done blocks merge |
| Local model too weak for Plan or Check, producing plausible nonsense | medium | high | you disagree with most proposed gaps | API routing per step; compare on eval before deciding |
| API rate limits and outages stall runs | high | low | runs take hours | disk cache, cassettes, batch endpoints, resume |
| PDF parsing garbles two-column papers | medium | medium | extraction accuracy under 80 percent on IEEE papers | GROBID fallback; the 10-PDF parsing test set |
| Citation constraint bypassed by a prompt or model change | low | very high | any invalid key in a draft | validator is code, not prompt; eval requires 100 percent |
| Store schema changes break older tools | medium | medium | migration fails or a tool reads a null | migrations only, never manual edits; integration test per tool |
| Time: internship start and exams | high | medium | two consecutive weeks under 4 hours | slip, do not compress; drop list in section 4.4 |
| Over-trusting the suite on the honors paper | medium | high | you stop reading extraction spans | every gate requires a human action; Check routes to a different model than Write |
| Open-weight model licenses or availability change | low | low | model disappears from Ollama library | model name in config; record which one each run used |
| Papers with Code style service shutdowns (dataset or SOTA sources) | medium | low | a client starts returning errors | six independent sources; no single-source dependency |

### 14.1 Failure modes of the whole idea

- The suite works but you do not use it because labeling and gating feel slower than just doing the work. Signal: no runs for three weeks after Phase 1. Response: cut the gates down to Find labels and Check only; those two are where the value concentrates.
- Your topic is narrow enough that Find saturates at 150 papers and the learning-from-labels machinery never matters. That is a success, not a failure; skip section 6.5's classifier.
- A frontier model with web search does the Plan and Check jobs better than the suite. Possible. The suite's advantage is grounding in your store and your labels; if that advantage does not show up in the Phase 2 gate, route those steps to the API and keep the store.

### 14.2 Security and privacy

- Medical imaging data never enters the suite. Figures reads metric tables and pre-rendered example images you choose; it never touches raw scans.
- API keys live only in config.local.toml and the environment.
- If any step is routed to an API, the run log records it, so you always know what left the machine.

### 14.3 What to reconsider at each gate

- After Phase 1: is the 80 percent recall real on a fresh set of held-out papers, or did tuning overfit the eval set? Build 10 new held-out papers and re-measure once.
- After Phase 2: did Write save time net of reading and fixing? If not, keep Cite and drop Write's drafting to a revision-only mode.
- After Phase 3: is Check's reviewer simulation catching things you miss, or restating things you know? Keep the audit; the simulation is optional.
- After Phase 4: is the orchestrator worth its maintenance, or do you run tools by hand anyway? Either answer is fine.

## 15. Appendix: APIs, models, libraries, reference systems

Everything below is free at the tiers listed. Limits and model names are approximate as of September 2026 and must be verified when each phase starts.

### 15.1 Data APIs

| Service | Used for | Key | Documentation |
| --- | --- | --- | --- |
| OpenAlex | works search, citation graph, OA links, retraction flag | none; add email for polite pool | docs.openalex.org |
| Semantic Scholar Graph API | search, SPECTER embeddings, references and citations, recommendations | free key | api.semanticscholar.org |
| arXiv API | newest preprints, full source download | none | info.arxiv.org/help/api |
| PubMed E-utilities | clinical and medical physics venues | optional free key | ncbi.nlm.nih.gov/books/NBK25501 |
| Crossref REST API | authoritative DOI metadata, retractions | none; add email | api.crossref.org |
| Unpaywall | best open-access PDF per DOI | none; email required | unpaywall.org/products/api |
| Europe PMC | biomedical search, open-access full text as XML, citations | none; polite use | europepmc.org/RestfulWebService |
| DBLP | canonical computer science venue and series metadata | none; polite rate | dblp.org/faq/How+to+use+the+dblp+search+API |
| OpenReview | ML venue submissions and reviews before DOIs exist | none | docs.openreview.net/reference/api-v2 |
| CORE | open-access full text from institutional repositories | free key; open at lower limits without one | core.ac.uk/services/api |
| Springer Nature | Springer and LNCS metadata and open access, covers MICCAI | free key; 100 requests per minute on the open access tier | dev.springernature.com |
| bioRxiv and medRxiv | preprints arXiv does not carry | none | api.biorxiv.org |
| Zotero local API | library sync, PDF matching | none | zotero.org/support/dev/web_api/v3/start |

Phase 0 builds the first eight rows above. OpenReview, CORE, Springer Nature and bioRxiv arrive in Phase 1 and must earn their place on the section 6.7 recall ablation. IEEE Xplore, ResearchGate, Google Scholar, Scopus and Web of Science are rejected; see ADR 0002.

### 15.2 Models and serving

| Need | Choice | Notes |
| --- | --- | --- |
| Scientific paper embeddings | SPECTER2 base plus adapters (allenai on Hugging Face) | proximity adapter for search; run via sentence-transformers |
| Chunk embeddings for in-paper retrieval | a general text embedding model under 1B parameters | SPECTER2 is document-level; use a general model for passages |
| Local LLM serving | Ollama | simplest; JSON mode; fits the model layer's HTTP backend |
| Higher-throughput local serving | vLLM | only if batch extraction becomes slow |
| 7B to 8B instruct (expansion, rerank) | best current open instruct model in that class at 4 to 5 bit | pick at Phase 1 start |
| 14B to 32B instruct (extract, plan, write, check) | best current open instruct model that fits 24 GB at 4 bit with 8k or more context | pick at Phase 1 start; 32B at 4 bit is tight, leave room for context |
| Optional API for plan and check | any frontier model via OpenAI-compatible endpoint | per-step routing only |
| Optional cross-encoder reranker | a small open cross-encoder | Phase 1 stretch goal |

### 15.3 Libraries

| Purpose | Library |
| --- | --- |
| Config and records | pydantic, pydantic-settings, tomllib; database: psycopg 3, SQLAlchemy Core, Alembic, pgvector, testcontainers |
| HTTP with retries | httpx, tenacity |
| Rate limiting | a small token-bucket implementation or the limits package |
| Test cassettes | vcrpy or respx |
| Embeddings | sentence-transformers; pgvector for similarity search |
| PDF parsing | pymupdf; GROBID via Docker as fallback |
| LaTeX parsing and compile check | pylatexenc, a minimal tectonic or latexmk wrapper |
| BibTeX | bibtexparser |
| Plotting | matplotlib, seaborn optional |
| Experiment readers | mlflow client, wandb export API |
| Terminal review view | rich or textual |
| Formatting and lint | ruff |

### 15.4 Reference systems to read before each phase

| Phase | Read | Why |
| --- | --- | --- |
| 0 to 1 | PaperQA2 (github.com/future-house/paper-qa) | agentic retrieval over papers with citation grounding; its metadata clients and evidence design |
| 1 | Ai2 ScholarQA (github.com/allenai/ai2-scholarqa-lib) | multi-paper synthesis over Semantic Scholar snippets |
| 1 | GPT Researcher (github.com/assafelovic/gpt-researcher) | planner and sub-question expansion patterns |
| 2 | Agent Laboratory (github.com/SamuelSchmidgall/AgentLaboratory) | human-in-the-loop stages, literature to plan to paper flow |
| 2 | STORM (github.com/stanford-oval/storm) | outline-first, cited article generation |
| 2 | Beel et al. 2025 audit of the AI Scientist (arXiv 2502.14297) | the concrete failure modes Plan and Check are designed to avoid |
| 3 | Curie (github.com/Just-Curieous/Curie) | experimental rigor enforcement ideas for the Check checklist |
| 3 | AIDE (github.com/WecoAI/aideml) | run-and-verify loop for generated scripts |
| 4 | Zotero MCP (github.com/54yyyu/zotero-mcp) and MLflow MCP server | how others expose the same stores to agents, if you later add an MCP interface |

### 15.5 Glossary of the suite's own terms

- Canonical ID: the single identifier per paper defined in section 2.2.
- Channel: one of the three discovery methods in Find.
- Evidence span: verbatim text plus page that a stored fact came from.
- Fact ID: a reference to an extraction row or result cell that Write must use instead of a literal number.
- Gate: a point in the pipeline where a human must act before the next tool runs.
- Run: one invocation of one tool with a recorded config snapshot.
- Stale: an output whose inputs changed after it was produced.
