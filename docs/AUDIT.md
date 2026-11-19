# Audits of teammates' branches (Exercise 3)

## Audit 1: mpkcb21/bikeshare-open, branch `exercise4-target-transform`

**Repo and branch:** https://github.com/mpkcb21/bikeshare-open, branch
`exercise4-target-transform`, commit `2303b25`. Branch diff against `main`:
one file, `src/ex4_target_transform.py` (104 lines added).

**Auditor:** a fresh `leakage-auditor` subagent started in this session, which
did not produce the branch. It ran read-only against a scratch clone of the
branch, with no `make` targets and no writers to `reports/` or `data/`.

**Model:** `leakage-auditor` subagent, model inherited from the session
(Claude). The subagent's own model choice is not recorded here.

### Auditor report (verbatim)

```text
Review of branch exercise4-target-transform (commit 2303b25), src/ex4_target_transform.py, against the five checks. Read-only; nothing in the repo was modified, no make targets or report/data writers were run.

Checks 1-3 pass.
- Leakage: features are cnt_lag_1 = shift(1), cnt_lag_7 = shift(7), cnt_roll_7 = shift(1).rolling(7) (src/features.py:76-78), built on the reindexed calendar. The ratio, diff and log forward transforms use only the target at row t. Each inverse uses a column from the same row that is known before t (cnt_roll_7, cnt_lag_7, cnt_lag_1). I perturbed cnt on 2012-05-20, 2012-06-01 and 2012-06-02 and confirmed that the lag features at 2012-06-01 do not change.
- Fits: _fit_predict and _persistence fit only on `train` (ex4 lines 58, 63). The ridge scaler is fit on train only. PersistenceBaseline.fit is a no-op.
- Split: temporal_split is date-based. The default run scores validation only (lines 87-89). --final is the only path that touches test (lines 82-86).
- Calendar gap: the reindex handles the 2011-03-10 gap. Lags are shift-by-row on the reindexed frame, so they are correct.
- Row loss: 728 raw rows become 714 model rows (348/182/184). The 14 lost rows are the 7 warmup days plus 2011-03-11..03-17, all of which are NaN-driven. This is expected and not a number-changing problem. I did not treat it as a finding.

Check 1 holds for casual/registered/cnt, cnt_2d_bfr and the other forbidden columns. None appear in the feature list.

Check 2: the selection was made on validation. The commit message for 1f31033 says "Chosen on validation: hgb + ratio_roll7", and I reproduced its validation table exactly (hgb ratio_roll7 is the best hgb row on both R2 and MAE). The test numbers in 2303b25 also reproduce exactly (hgb ratio_roll7 0.604 / 868.1; persistence 0.510 / 840.1; mean -2.144 / 2847.7). Note that I computed the test numbers in memory to check them, so test has now been looked at twice in total. Selection did not change.

Finding 1 (check 5, required baseline missing): src/ex4_target_transform.py lines 95-96 and 98-99 report persistence but never report the mean baseline. CLAUDE.md requires both next to every model. The missing numbers are validation mean R2 -0.932 / MAE 2002.2 and test mean R2 -2.144 / MAE 2847.7. Fix: add a row for baseline_mean, fitting DummyRegressor(strategy="mean") on train[cols] and scoring it on `part` in the same way as persistence. This does not change any model number, but the required baseline is absent.

Finding 2 (conclusion is overstated): the test result does not show that hgb+ratio_roll7 beats persistence on every metric. On test, R2 is 0.604 vs 0.510 for persistence, but MAE is 868.1 vs 840.1, so the chosen model has higher MAE than yesterday's count. On validation it wins on both (MAE 683 vs 901). Any write-up of this result should say that the R2 gain on test comes with a slightly worse MAE than persistence. Fix: report both metrics for persistence and the chosen model side by side, and state the MAE result in the write-up. Do not describe the transform as beating persistence without that caveat.

Minor, not a method finding: the choice was made among 10 configurations (5 transforms x 2 models) on a 182-row validation set. The margin is large (0.736 vs next-best 0.649 R2 for the same kind of model), so the choice itself is defensible.

Out-of-scope observation (no number changes): the branch is based on ccf8c68, while main has moved on to e6749f6. `git diff main` therefore shows deletions of REPORT.md, reports/metrics.json, reports/audit.jsonl and docs/DECISIONS.md. Merging the branch as-is would delete those files. Rebase onto main before merging.
```

### What I agree with, and what I checked

- **Finding 1 (missing mean baseline): agree.** I read `src/ex4_target_transform.py`
  and the only baseline it scores is `baseline_persistence` (lines 62-64, 95-96).
  The mean baseline is absent. This changes no number, but CLAUDE.md requires it.
- **Finding 2 (overstated conclusion): agree.** Test R² is higher for the
  transformed hgb (0.604 vs 0.510), but its MAE is higher too (868 vs 840). A
  write-up that says the transform "beats persistence" without the MAE caveat
  overstates the result.
- **Minor point (10 configurations on 182 validation days): agree.** The
  selection is a small-sample choice, but the gap to the next candidate is
  large enough that it is not the main concern.
- **Out-of-scope rebase note: agree.** I checked the branch's diff against
  `main`, and merging it as-is would delete files.
- **Checks 1-3 and the calendar and row-loss points: agree, after reading the
  code.** The features are shifted before rolling (`src/features.py:76-78`
  in the friend's repo), and the forward and inverse transforms use only
  columns known at prediction time. The default run scores validation only.
- **Not verified by me:** the auditor's perturbation test (changing `cnt` on
  2012-05-20, 06-01 and 06-02 and checking lag features) and the test-set
  numbers. I did not reproduce either.

### Verdict

Nothing the auditor reported changes a number, so the branch's validation and
test figures are not invalidated. But two things need fixing before the result
goes into a report. The mean baseline must be added, and the test result must
be reported with its MAE next to persistence's. The branch should also be
rebased onto `main` before merging. The auditor also computed the test numbers
to check them, which means the test split has now been looked at twice; the
branch's own commits say it was scored once, so that count should be stated
honestly in the friend's DECISIONS.md.
