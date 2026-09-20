---
title: "Scholium. Tool 1: Find"
author: "Veerbhadra Mahant"
date: "18 September 2026"
---

Section 6 of the full plan. Requires Phase 0 complete.

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
