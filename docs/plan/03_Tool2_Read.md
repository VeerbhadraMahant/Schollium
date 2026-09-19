---
title: "Scholium. Tool 2: Read and Synthesize"
author: "Veerbhadra Mahant"
date: "18 September 2026"
---

Section 7 of the full plan. Requires Find at 80 percent recall.

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

