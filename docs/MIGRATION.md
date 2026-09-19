# Migrating to Claude Code

How to take this bundle into a fresh repository and start Phase 0 with Claude Code, so the plan and the code live together and every session starts from the same context.

## 1. Set up the repository

1. Create an empty repository named `scholium` (local, then push to a private GitHub repo).
2. Unzip this bundle into it. The layout is already the one CLAUDE.md expects: `CLAUDE.md`, `CHANGELOG.md`, `.gitignore`, `docs/`, `prompts/`, `eval/`, `projects/_template/`.
3. Commit as `docs: initial plan and Claude Code context`.
4. Install prerequisites on the machine: Python 3.11 or newer, Docker with Compose, Ollama with at least one 7B to 8B instruct model pulled, git.
5. Create free API keys: Semantic Scholar (required for embeddings and batch endpoints), PubMed E-utilities (optional). Note the email you will use for OpenAlex, Crossref and Unpaywall polite pools. These go in `config.local.toml`, never in git.

## 2. How Claude Code uses these files

- `CLAUDE.md` is read automatically at the start of every session. It carries the rules, stack and conventions. Keep it under about 300 lines; move detail into docs/.
- `docs/STATUS.md` is the session-to-session memory of progress. Claude Code should read it first and update it last. If it drifts from reality, fix it before doing anything else.
- `docs/plan/*.md` are the specifications. Point Claude Code at the exact file for the work in hand rather than the full plan; the full plan is for architectural questions.
- `docs/adr/` records decisions. Any change to the stack or store schema design gets an ADR before code.
- `prompts/` and `eval/` are empty on purpose; they fill in as tools are built.

## 3. First session prompt

Paste this as the first message in Claude Code, from the repository root:

> Read CLAUDE.md, then docs/STATUS.md, then docs/plan/01_Foundation_Phase0.md in full. We are starting Phase 0, Day 1 to 2 (skeleton). Before writing anything, list the files you intend to create and the decisions you are making that the plan leaves open (argument parser choice, exact config schema, Docker image tag). Wait for my confirmation, then build the skeleton, the config loader and the `doctor` command with tests, run ruff and the tests, and update docs/STATUS.md and CHANGELOG.md.

## 4. Session rhythm that keeps the plan and the code aligned

1. Start: "Read CLAUDE.md and docs/STATUS.md. What is the next unchecked item and which plan file covers it?"
2. Work in a branch named as the plan says. Ask Claude Code to write tests with the code, not after.
3. End: "Run ruff and the fast tests. Run the eval if this tool has one. Update docs/STATUS.md (checklist, gate table, eval scores) and add one CHANGELOG line. Tell me what is left in this phase."
4. Once a week: "Compare docs/STATUS.md against the repository and list any drift."

## 5. Prompts for each phase gate

- Phase 0 gate: "Walk the Phase 0 checklist in docs/STATUS.md item by item and demonstrate each one is true by running it."
- Phase 1 gate: "Run eval/find and eval/read. Report recall at 50, 100 and 200 and field accuracy per field. Do not tune anything; only report."
- Phase 2 gate: "Draft the related-work section of projects/<name> through plan, write and cite. Report every citation key and confirm each resolves to a store row with a DOI or arXiv ID."
- Phase 3 gate: "Run eval/figures and eval/check. Report which of the 18 planted issues were found and every false positive."
- Phase 4 gate: "Run the full pipeline on projects/<name> with every gate exercised, then write docs/retrospective.md."

## 6. Things Claude Code should refuse or question

These are in CLAUDE.md under "Things to push back on". If Claude Code does one of them without asking, that is a sign CLAUDE.md is not being read; check the file is at the repository root and the session started there.

## 7. What is not in this bundle

- No source code. The plan is deliberately code-free so the implementation decisions are made in the repository with tests, not in a document.
- No model names. Pick the best open instruct models that fit 24 GB of VRAM at the start of Phase 1, record them in config and in an ADR.
- No PDFs. The PDF versions of the plan are for reading; the markdown here is what Claude Code ingests. Keep them in sync by regenerating PDFs from these files, not by editing PDFs.
