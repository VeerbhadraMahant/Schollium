---
title: "Scholium. Tool 7: Check"
author: "Veerbhadra Mahant"
date: "18 September 2026"
---

Section 12 of the full plan. Requires Cite verdicts and the figure registry.

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

