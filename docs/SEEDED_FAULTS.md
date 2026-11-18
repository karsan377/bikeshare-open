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
