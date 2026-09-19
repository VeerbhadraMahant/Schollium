---
title: "Scholium. Tool 6: Figures"
author: "Veerbhadra Mahant"
date: "18 September 2026"
---

Section 11 of the full plan. Requires result tables in the store.

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

