# Bikeshare demand: report

## Results

Temporal split: train = 2011 (302 rows after warm-up), validation = H1 2012
(182 days), test = H2 2012 (184 days). All rows are from the same 668-row
feature table, so "before" and "after" differ only by the `cnt_roll_30`
column. Values are from `reports/metrics.json` at HEAD (pinned environment:
pandas 3.0.5, scikit-learn 1.9.1, numpy 2.4.6) for the "after" rows; the
"before" rows were computed from the same pipeline with `cnt_roll_30`
removed. Both sets were computed after the feature decision was made from
validation.

| Model | Feature set | Valid R² | Valid MAE | Test R² | Test MAE |
|---|---|---|---|---|---|
| baseline_mean | before | -0.6637 | 1863.1 | -1.7308 | 2638.0 |
| baseline_persistence | before | +0.4507 | 900.6 | +0.5099 | 840.1 |
| ridge | before | +0.6478 | 832.6 | +0.5807 | 949.0 |
| hgb | before | +0.1698 | 1344.5 | -0.6412 | 2073.1 |
| baseline_mean | after | -0.6637 | 1863.1 | -1.7308 | 2638.0 |
| baseline_persistence | after | +0.4507 | 900.6 | +0.5099 | 840.1 |
| ridge | after | +0.6805 | 783.1 | +0.6213 | 884.1 |
| hgb | after | +0.2292 | 1287.8 | -0.5492 | 2016.9 |

The "after" rows match `reports/metrics.json` to the printed digit. A clean
`pip install -r requirements.txt` in a fresh environment, followed by
`make all`, reproduces that file byte-for-byte.

## Headline finding

Under a temporal split, ridge (R² 0.62, MAE 884) and persistence (R² 0.51,
MAE 840) are close on test: ridge leads on R² and persistence on MAE. The
mean baseline is far below zero (R² -1.73, MAE 2638). Gradient boosting is negative on test (R² -0.55) yet
still well ahead of the mean baseline. The reason is extrapolation: ridership
grew about 65% from 2011 to 2012, and a tree cannot predict above the largest
training value, so it fails on the 2012 days above the 2011 maximum (on the
714-row table, 56% of test days). The leaky model that includes `casual` and
`registered` scores R² 1.000 because it learns that they sum to `cnt`; that
number is invalid and is not a result. Adding the 30-day trailing mean
(`cnt_roll_30`) raised ridge's validation R² from 0.648 to 0.681 and lowered
its validation MAE from 833 to 783. It also raised hgb's validation R² from
0.170 to 0.229. I kept the feature: both deltas exceed the 0.01 threshold.
Its test effect is +0.04 R² for ridge, but test was not used to decide it.

## Exercise 4: target transformation

Validation only; the test split was not scored for this section. Gradient
boosting's problem is the output range, so I tried two transforms on the
same features and the same training rows.

| Target | hgb valid R² | hgb valid MAE |
|---|---|---|
| raw `cnt` (headline model) | +0.229 | 1288 |
| log1p(`cnt`) | +0.167 | 1339 |
| ratio `cnt / cnt_roll_30` | +0.681 | 722 |

The control is the trailing 30-day mean used alone as the forecast: valid R²
+0.548, MAE 906. The ratio model is ahead of that control by 0.13 R² and
MAE 184 rides. Its R² equals ridge's (0.681) and its MAE is lower (722 vs 783).
The transform is defensible as a variant because it is a standard fix for a
level that drifts. The target is expressed relative to a level known at
prediction time, so it uses no future information. The tree's output range is
now relative, so the 2011 ceiling no longer caps it. It is not defensible as
the headline. I tried three transforms and picked the best on 182 validation
days, so part of the gain is selection. The honest claim is "a trailing-mean
anchored tree matches ridge on validation", which is weaker than "the tree
beats ridge". The headline metrics stay untransformed, as the assignment
requires. The ratio model's test score is not reported because the test set was
not touched for this exercise.

## Exercise 5: ridge vs persistence

On test, ridge beats persistence on R² (0.621 vs 0.510) and loses on MAE (884
vs 840). On validation it wins both (R² 0.681 vs 0.451; MAE 783 vs 901). My
position is that ridge is worth deploying over "yesterday again", but only
where large misses cost more than typical ones, such as staffing for peak
days. The R² gain comes mostly from pulling extreme forecasts toward the
middle, and an earlier diagnostic (on the 714-row table, before `cnt_roll_30`) showed
that the ridge-minus-persistence difference is negatively correlated with
persistence (-0.68). On a typical day persistence is closer: on that table,
ridge was nearer the actual count on about 39% of test days. A decision that charges per ride of error should use persistence, and
ridge should be kept as the model to monitor, with persistence reported
alongside it at every update.

## Attribution

Model used: `bikeshare-coder` (qwen3.5:9b, 64k context, via Ollama) for the
batch audit in `reports/audit.jsonl`. Earlier sessions for this assignment ran
on Claude Opus through Claude Code, per the author. Later steps ran in Claude
Code with a Claude Haiku 5.5 assistant, with Sonnet 5.5 used for one planning
step. The author moved between Claude Code on Anthropic models and Claude Code
pointed at a local Ollama server. The model changed at least twice, so the
results should not be compared across model sizes.

Agent-generated, reviewed and committed by the author:
- `src/train.py` (rewritten from the spec; the starter's version was removed first, in a separate commit).
- The `cnt_roll_30` function in `src/features.py`, and the `LAG_WARMUP` change in `src/config.py`.
- `RAW_SOURCE_COLS` and `RAW_SHA256` in `src/config.py`.
- `test_every_raw_column_is_classified` and `test_raw_csv_is_unmodified` in `tests/test_contract.py`.
- The hook change in `.claude/hooks/check_leakage.sh`.
- The `ablation` skill in `.claude/skills/ablation/SKILL.md`.
- The Exercise 4 scripts, which were run in scratch and are not committed.

Decisions that were the author's (each traces to a line in `docs/DECISIONS.md`):
- What to predict: daily `cnt`, from calendar, weather and lagged demand.
- What counts as leakage: `casual`, `registered`, the time indexes and `cnt_2d_bfr` (the first three lines of DECISIONS.md).
- How to split: by date, 2011 / H1 2012 / H2 2012. Test not used for any decision.
- Which baselines: mean and persistence, reported beside every score.
- Keep `cnt_roll_30`: validation deltas recorded as a dated DECISIONS line.
- Keep `cnt_roll_7`: ablation delta recorded as a dated DECISIONS line.
- Exercise 4 is a validation-only variant; the headline stays untransformed.
- Whether the answer is believable: ridge beats persistence on R² and not on MAE on test, and the report says so.

Incidents the author should know about:
- A headless `agent/audit.py` run overwrote `reports/metrics.json` with
  scikit-learn 1.7.2 values; the file was restored from HEAD. The audit's
  "no findings" result does not rule out this kind of change, and I did not
  check whether the auditor called `check_identity`.
- The audit ran with the workspace untrusted, so the project's permission
  allow and deny rules were ignored. The auditor's tools are restricted only
  by `allowed_tools` in the script.
