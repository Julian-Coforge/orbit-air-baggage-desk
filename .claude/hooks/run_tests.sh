#!/usr/bin/env bash
# Stop hook: runs pytest when Claude tries to finish.
# Exit 0 lets Claude stop. Exit 2 sends the failure output back to Claude
# so it keeps working until the tests pass.
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0

if [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
else
  PY=python3
fi

out=$("$PY" -m pytest -q 2>&1)
rc=$?

# 0 = all tests passed, 5 = no tests collected yet (before the first branch).
if [ "$rc" -eq 0 ] || [ "$rc" -eq 5 ]; then
  exit 0
fi

echo "pytest failed. Fix the code, not the tests:" >&2
echo "$out" >&2
exit 2
