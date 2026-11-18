---
name: ablation
description: Drop one feature, retrain ridge and hgb, and report the validation R^2 and MAE change. Use when asked whether a feature earns its place, or to ablate a named column.
allowed-tools: Read, Bash(python -m src.*), Bash(python -c*), Bash(.venv/bin/python*)
---

# Ablation: $ARGUMENTS

Measures what removing one feature does to validation performance. Validation
only. Never read or score the test split here.

1. **Name the column.** $ARGUMENTS must be one of the current features. Check it
   against `feature_columns()`. If it is not a feature, say so and stop.

2. **Score with and without it on validation.** Build the table with
   `build_features(load_raw())`, split with `temporal_split` (train and valid
   only; discard test), and fit `ridge` and `hgb` from `MODELS` on train with
   the full feature list, then with the named column removed. Report R^2 and MAE
   on valid for both, plus the delta. Use the same rows for both runs.

3. **Interpret.** If validation R^2 improves by less than 0.01 when the feature
   is kept, say so plainly and recommend dropping it. The validation set is 182
   days and the R^2 noise is larger than 0.01.

4. **Record.** Append one dated line to `docs/DECISIONS.md`: the feature, the
   validation delta for each model, and the recommendation.

Do not change `src/`, `reports/metrics.json`, or the test split. An ablation
is a finding, not a model change; if the feature is dropped, that is a separate
`/new-feature` or code change.
