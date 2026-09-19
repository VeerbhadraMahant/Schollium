---
title: "Scholium. Tool 3: Plan"
author: "Veerbhadra Mahant"
date: "18 September 2026"
---

Section 8 of the full plan. Requires Read extractions.

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

