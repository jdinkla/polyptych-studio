#!/bin/bash
# PostToolUse hook: auto-format + lint-fix Python files after Claude edits them.
# Receives the tool-call JSON on stdin; acts only on .py files.
set -euo pipefail

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')

[[ "$file_path" == *.py ]] || exit 0
[[ -f "$file_path" ]] || exit 0

# Format only — idempotent, no semantic changes. Lint-fixing (e.g. removing
# "unused" imports) is intentionally left to `just lint`, since on a per-edit
# hook it would strip imports added in one edit before they're used in the next.
uv run ruff format "$file_path" >/dev/null 2>&1 || true

exit 0
