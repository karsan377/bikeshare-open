# Seeded faults and failing runs

## Feature test written first: cnt_roll_30

Test: `tests/test_leakage.py::test_cnt_roll_30_is_mean_of_prior_30_days`.
Committed before the feature, as required. The test hand-sums cnt over the
30 calendar days strictly before 2011-06-15, from the raw CSV.

Failing run, before `cnt_roll_30` exists (`python -m pytest ... --tb=line`):

```
F                                                                        [100%]
=================================== FAILURES ===================================
/Users/karthik/.pyenv/versions/3.11.12/lib/python3.11/site-packages/pandas/core/generic.py:6318: AttributeError: 'DataFrame' object has no attribute 'cnt_roll_30'
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_cnt_roll_30_is_mean_of_prior_30_days - Att...
1 failed in 0.27s
```

Full `make test` before the feature: 14 passed, 1 failed (this test). The
other 14 are green, so the failure is only the missing feature.

## How the faults were run

Each fault was applied by a script in the repo, the hook was run by hand
with the same JSON payload the harness sends (`{"tool_name":"Edit",
"tool_input":{"file_path":...}}`), then the file was restored with
`git checkout`. The hook was **not** fired by Claude Code's own Edit tool in
this session, so the stderr below is the hook script's output, not a
harness-delivered system message.

**Test totals:** the suite had 16 tests until `test_raw_csv_is_unmodified` was
added, then 17. Faults 2 and 3 ran against 16; fault 1 was re-run and fault 4's
hash check ran against 17. Each block shows the total at the time it was run.
Some hook stderr blocks are excerpts (marked `...`); the lines shown are verbatim.

**Turns to fix:** 0 agent turns. Each seeded fault was applied by a script,
not by an agent, and was undone with one `git checkout`. No agent iterations
were needed, so there is no agent turn count to report.

## Fault 1: forbidden column reaches the feature set

Change (`src/features.py`, `feature_columns`):

```diff
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN - {"registered"}]
```

`make test` (red):

```
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 16 passed in 1.04s
make: *** [test] Error 1
```

Hook stderr, exit 2:

```
Tests failed after editing /Users/karthik/Desktop/DSC180/bikeshare-open/src/features.py:
...
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'registered'}
...
tests/test_leakage.py:31: AssertionError
```

Caught by: `test_no_forbidden_features`. Restored; `make test` 17 passed; hook exit 0.

## Fault 2: `.shift(1)` deleted from cnt_roll_7

Change (`src/features.py`):

```diff
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(7).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(7).mean()
```

`make test` (red):

```
E       assert np.float64(4248.0) == 4309.857142857143 ± 0.00430986
E         Obtained: 4248.0
E         Expected: 4309.857142857143 ± 0.00430986
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 15 passed in 1.05s
```

Hook stderr, exit 2: `Tests failed after editing .../src/features.py:` followed
by the same assertion (`assert feats.set_index("dteday").cnt_roll_7[date] ==
pytest.approx(expected)`, Expected 4309.857142857143, Obtained 4248.0).

Caught by: `test_rolling_mean_excludes_today`. Restored; green; hook exit 0.

## Fault 3: weather encoder's raise removed

**3a, raise removed alone: not caught.** `make test` stayed green (16 passed)
and the hook exited 0. The labels in the data are all in `WEATHER_ORDER`, so
the raise never fires on this data. Removing it changes nothing observable
here. That is a finding: the raise is a guard for future data, not a
behaviour the current tests exercise.

**3b, raise removed and `BAD` missing from `WEATHER_ORDER`: caught by the row-loss
test, but the starter hook missed it.** This is the failure the raise exists
to prevent: BAD-weather days become NaN and are silently dropped.

Change (`src/features.py`):

```diff
-WEATHER_ORDER = {"GOOD": 0, "MISTY": 1, "BAD": 2}
+WEATHER_ORDER = {"GOOD": 0, "MISTY": 1}
...
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
+        pass  # raise removed
```

`make test` (red):

```
E       AssertionError: lost 78 rows; expected at most 60
E       assert 78 <= 60
FAILED tests/test_contract.py::test_only_expected_rows_are_dropped - Assertio...
1 failed, 15 passed in 1.06s
make: *** [test] Error 1
```

Hook with the **starter** hook (which ran only `tests/test_leakage.py`): exit 0,
no stderr. The hook missed a red suite. The row-loss test is in
`test_contract.py`, outside the hook's scope.

**Fix to the hook.** `.claude/hooks/check_leakage.sh` now runs the whole suite
(`python -m pytest tests/ -q`). Rerunning fault 3b with the fixed hook:

```
hook exit: 2
tests/test_contract.py:43: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_contract.py::test_only_expected_rows_are_dropped - Assertio...
1 failed, 15 passed in 1.07s
```

Restored; hook exit 0.

## Fault 4: a raw-data edit the PostToolUse hook cannot see (Bash `cp` into data/raw/)

Run in a scratch copy, so the real raw CSV was never touched. One temperature
value on line 102 (2011-04-14) changed from 13.9725 to 14.0225, a plain text
substitution with the rest of the file byte-identical. Copied in with
`cp`, as a Bash command would do.

What happened:
- The hook received a `Bash` payload, so its `matcher` (`Edit|Write`) and its
  `*src/*.py` guard both skipped it. Exit 0, no stderr.
- `make test` was **green** on the edited CSV: 16 passed, with the old hook scope
  and the leakage tests all passing.
- `make data` was **green**: `OK ingest: 728 rows, 2011-01-03 -> 2012-12-31`.
  The shape assertion does not check values.
- sha256 changed: `f33f3286...` instead of `a6bed157...`. Nothing in the
  pipeline compared it.

What would catch it, and what I implemented:
- **Implemented:** a pinned hash, `RAW_SHA256` in `src/config.py`, and
  `test_raw_csv_is_unmodified` in `tests/test_contract.py`. On the edited scratch
  copy, `make test` goes red:

```
E       AssertionError: raw CSV changed: sha256 f33f328608cd8c17cf23b3769a909aea57de1c2341871d0bf8f01e923bb2a9b9
E       assert 'f33f328608cd...01e923bb2a9b9' == 'a6bed1577f6e...0c86a0b5ad9dc'
FAILED tests/test_contract.py::test_raw_csv_is_unmodified - AssertionError: r...
1 failed, 16 passed in 1.04s
```

  This catches the edit on the next `make test`, not at the moment of the
  `cp`. The gap is the time between the write and the next test run.
- **Not implemented, named:** a `PreToolUse` hook on `Bash` that blocks any
  command whose text writes to `data/raw/`, or a filesystem permission
  (`chmod -w data/raw`). Either would stop the write itself. The
  `Write(./data/raw/**)` deny rule in `.claude/settings.json` does not cover
  Bash, as the assignment notes.
