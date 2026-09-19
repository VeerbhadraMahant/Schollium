---
title: "Scholium. Tool 4: Write"
author: "Veerbhadra Mahant"
date: "18 September 2026"
---

Section 9 of the full plan. Requires an approved plan.

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

