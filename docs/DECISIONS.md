# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-18 Feature `cnt_roll_30` (mean of cnt over the 30 days before d, `shift(1)` before `rolling`). Availability: all 30 inputs are measured on or before d-1. Validation delta on the same 668-row table, pinned env: ridge R^2 0.648 -> 0.681 (MAE 833 -> 783); hgb 0.170 -> 0.229 (MAE 1345 -> 1288). Kept: both deltas exceed 0.01. The feature commit message quotes hgb +0.060 from an earlier scikit-learn; the pinned delta is +0.059.
- 2026-11-18 `LAG_WARMUP` 7 -> 30. `cnt_lag_7` and `cnt_roll_7` are written with literal windows so the change does not reach them. Rows 714 -> 668: exactly the 60-row bound in `test_contract` (30 warm-up plus 30 days after the 2011-03-10 gap). Training rows fall 348 -> 302, so pre-feature numbers from the 714-row table are not comparable to the table in REPORT.md; the pre-feature comparison uses the same 668 rows.
- 2026-11-18 Six raw columns (`holiday`, `workday`, `weather`, `season`, `mnth`, `weekday`) go in `RAW_SOURCE_COLS`. The first three feed features; the last three are superseded by `dteday`-derived features. `test_every_raw_column_is_classified` fails on any new raw column until it is classified.
- 2026-11-18 Raw CSV pinned by sha256 in `src/config.py`; `test_raw_csv_is_unmodified` catches a Bash `cp` that the PostToolUse hook cannot see. Caught on the next `make test`, not at write time.
- 2026-11-18 Hook runs the whole suite, not only `test_leakage.py`. The row-loss test lives in `test_contract.py`; the starter hook exited 0 on a red row-loss suite (seeded fault 3b).
- 2026-11-18 numpy pinned to 2.4.6. 2.5.3 is not on the package index. A clean venv from `requirements.txt` reproduces `reports/metrics.json` exactly.
- 2026-11-18 Ablation of `cnt_roll_7` (validation only, `/ablation`): ridge +0.021, hgb +0.033 when kept. Kept.
- 2026-11-18 Exercise 4, validation only, test not touched for it. Raw hgb valid R^2 0.229; log1p target 0.167; ratio `cnt / cnt_roll_30` 0.681 (MAE 722). Control: trailing 30-day mean alone 0.548 (MAE 906). The ratio transform is a standard fix for trend and uses only inputs known at d. It was chosen from three candidates on 182 validation days, so the gain is partly selection. Reported as a variant against the trailing-mean control; not in the headline metrics.
- 2026-11-18 Test-set metrics were printed by `make train` once, after the feature decisions above were made from validation. No decision used them. Exercise 4 was not scored on test.
