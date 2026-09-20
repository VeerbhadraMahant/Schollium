---
title: "Scholium. Integration, risks and appendix"
author: "Veerbhadra Mahant"
date: "18 September 2026"
---

Sections 13 to 15 of the full plan: orchestrator, GitHub tracking, risks and reference material.

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
