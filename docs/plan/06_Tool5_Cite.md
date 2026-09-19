---
title: "Scholium. Tool 5: Cite"
author: "Veerbhadra Mahant"
date: "18 September 2026"
---

Section 10 of the full plan. Runs on any .tex plus .bib pair.

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

