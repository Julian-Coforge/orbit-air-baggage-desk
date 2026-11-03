#!/usr/bin/env bash
# Stop hook: runs pytest when Claude tries to finish.
#
# Exit 0 lets Claude stop. Exit 2 blocks the stop and sends the pytest output
# back to Claude, so it keeps working until the tests pass.
#
# Loop guard: Claude Code sets "stop_hook_active": true in the hook input when
# Claude is already continuing because this hook blocked it. In that case the
# hook does not block a second time; it lets Claude stop and shows the user a
# warning, so a failure Claude cannot fix never turns into an endless loop.
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0

input=$(cat)
if printf '%s' "$input" | grep -Eq '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
  already_retried=1
else
  already_retried=0
fi

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

if [ "$already_retried" -eq 1 ]; then
  echo '{"systemMessage": "Stop hook: tests still fail after one retry. Read the pytest output yourself before continuing."}'
  exit 0
fi

echo "pytest failed. Fix the code, not the tests:" >&2
echo "$out" >&2
exit 2
