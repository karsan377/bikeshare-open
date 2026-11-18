#!/usr/bin/env bash
# PostToolUse hook: re-run the leakage tests whenever src/ changes.
#
# This runs AFTER the edit has landed, so it cannot prevent the write. What
# exit 2 does is send stderr back to Claude as a system message, so the
# failure is in front of the agent immediately and it cannot carry on as if
# the edit were fine. To make "done" itself conditional on green tests, add
# a Stop hook that runs `make test` and exits 2 on failure (check
# stop_hook_active in the payload to avoid looping).
set -uo pipefail

payload=$(cat)
path=$(printf '%s' "$payload" | python3 -c \
  'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')

case "$path" in
  *src/*.py) ;;
  *) exit 0 ;;
esac

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
# Full suite, not just test_leakage.py: the row-loss bound lives in
# test_contract.py, and a silent encoder NaN was invisible to the leakage
# tests alone (see docs/SEEDED_FAULTS.md, fault 3b).
if ! out=$(python -m pytest tests/ -q 2>&1); then
  echo "Tests failed after editing $path:" >&2
  echo "$out" | tail -20 >&2
  exit 2
fi
exit 0
