#!/usr/bin/env bash
# STRETCH GOAL 1: PreToolUse hook that stops Claude editing anything in tests/.
# The tests are the spec. I can still edit them myself in VS Code; this only fires on
# Claude's Edit, Write and MultiEdit tools.

input=$(cat)

# Pull tool_input.file_path out of the hook JSON. python3 is used so this works without jq.
file_path=$(printf '%s' "$input" | python3 -c \
  'import json, sys; print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))' \
  2>/dev/null)

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
