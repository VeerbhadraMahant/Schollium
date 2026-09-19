# eval/

One folder per tool, each with the fixed evaluation set and a scoring script, plus `results.md` with one row per run: date, commit, prompt versions, model, score. Pass criteria are in the tool's plan file. Build the eval set before tuning, never after. A regression blocks the merge.
