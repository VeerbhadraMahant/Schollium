# AI research agent landscape (condensed survey, September 2026)

Background only. This is the survey that motivated Scholium, condensed to what matters for design decisions. It is not an execution document.

## Conclusion that drove the project

No single free, local, ML-focused system composes paper discovery, grounded reading, planning, citation-safe writing and verification. End-to-end "AI scientist" systems are cloud only, closed, expensive and oriented to biology or data analysis (Kosmos from Edison Scientific, Google Co-Scientist). Open systems each cover one layer and do not share state: PaperQA2 and Ai2 ScholarQA for grounded literature Q&A, Agent Laboratory and AI-Researcher for human-in-the-loop research pipelines, AIDE and MLE-bench scaffolds for experiment code, Zotero MCP servers for citations. Assembling these yourself around one store with your own relevance labels is the only route to the unified tool today.

## The three problems every existing system has

1. Citation accuracy. Generic chatbots fabricate references at high rates (Walters and Wilder 2023 measured 55 percent fabricated for GPT-3.5 and 18 percent for GPT-4, with substantive errors in a further 24 to 43 percent of real citations). Retrieval-grounded tools are far better, but a 2026 benchmark of deep-research agents still found factual citation accuracy of only 39 to 77 percent, dropping as tool calls increase. Scholium's response: citations are lookups from the store, never generated; Cite verifies support against full text.
2. Brittle experiment execution. On MLE-bench the best autonomous setup (o1-preview with AIDE) reached a Kaggle bronze in only 16.9 percent of tasks. The Beel et al. 2025 audit of Sakana's AI Scientist found many failed experiments, hallucinated numbers and misjudged novelty. Scholium's response: no autonomous experiments; results are read from MLflow, and Check audits every number against a table.
3. No local, unified, ML-specific system. Scholium's response: one Postgres store, one model layer, seven commands, human gates between them.

## Systems worth reading before each phase

| Phase | System | Why |
| --- | --- | --- |
| 0 to 1 | PaperQA2 (FutureHouse, MIT license) | Agentic RAG over PDFs with grounded citations; runs on local models via Ollama; see its metadata clients and evidence design |
| 1 | Ai2 ScholarQA / Asta (Allen AI, open source) | Multi-paper synthesis with tables over Semantic Scholar snippets |
| 1 | GPT Researcher (open source) | Planner and sub-question expansion; supports Ollama and local documents |
| 1 | Undermind, Elicit, Consensus (commercial) | The user experience to match for deep search and structured extraction |
| 2 | Agent Laboratory (Schmidgall et al., MIT license) | Human-in-the-loop literature to plan to paper flow; human feedback at each stage improved quality |
| 2 | STORM (Stanford, open source) | Outline-first, cited article generation |
| 2 | Beel et al. 2025, arXiv 2502.14297 | The concrete failure modes Plan and Check are designed to avoid |
| 3 | Curie (open source) | Experimental rigor enforcement; ideas for the Check reproducibility checklist |
| 3 | AIDE (Weco, open source) | Run-and-verify loop for generated scripts |
| 4 | Zotero MCP, MLflow MCP server, GitHub MCP server | How others expose the same stores to agents; relevant if Scholium later adds an MCP interface |

## Free data sources Scholium relies on

OpenAlex (no key, citation graph, abstracts, OA links, retraction flag), Semantic Scholar Graph API (free key, SPECTER embeddings, references and citations, recommendations), arXiv API, PubMed E-utilities, Crossref, Unpaywall. Papers with Code shut down in July 2025; its data is archived on Hugging Face and it is not a dependency.

## Things deliberately not built

- AI-text detection: high false positive rates on technical and non-native English prose, trivially evaded.
- A separate vector database or search engine: pgvector and Postgres full-text search cover both.
- A chat interface: commands with explicit inputs and outputs keep the tool precise.
