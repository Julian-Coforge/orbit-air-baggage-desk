#!/usr/bin/env bash
# STRETCH GOAL 1: PreToolUse hook that stops Claude editing anything in tests/.
# The tests are the spec. I can still edit them myself in VS Code; this only fires on
# Claude's Edit, Write, MultiEdit and NotebookEdit tools. It does not see shell commands.

input=$(cat)

# Pull the target path out of the hook JSON (file_path, or notebook_path for NotebookEdit).
# python3 is used so this works without jq. If the input cannot be read, block the edit
# rather than let it through unchecked.
if ! file_path=$(printf '%s' "$input" | python3 -c '
import json, sys
tool_input = json.load(sys.stdin).get("tool_input", {})
print(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
' 2>/dev/null); then
  echo "Blocked: could not read the hook input, so the edit was not checked." >&2
  exit 2
fi

# Make the path relative to the project so "tests/x.py" and "/full/path/tests/x.py" match.
project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"
relative="${file_path#"$project_dir"/}"

case "$relative" in
  tests/* | */tests/*)
    echo "Blocked: tests/ is the spec and cannot be edited by the agent." >&2
    exit 2
    ;;
esac
exit 0
