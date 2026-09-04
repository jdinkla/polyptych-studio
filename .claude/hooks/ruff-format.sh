#!/bin/bash
# PostToolUse hook: auto-format Python files after Claude Code or Codex edits.
# Supports Claude Code's file_path input and Codex's apply_patch command input.
set -euo pipefail

input=$(cat)
repo_root=$(git rev-parse --show-toplevel)

paths=()
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')
[[ -n "$file_path" ]] && paths+=("$file_path")

while IFS= read -r patch_path; do
  [[ -n "$patch_path" ]] && paths+=("$patch_path")
done < <(
  printf '%s' "$input" |
    jq -r '.tool_input.command // empty' |
    sed -nE \
      -e 's/^\*\*\* (Add|Update) File: //p' \
      -e 's/^\*\*\* Move to: //p'
)

# Format only — idempotent, no semantic changes. Lint-fixing (e.g. removing
# "unused" imports) is intentionally left to `just lint`, since on a per-edit
# hook it would strip imports added in one edit before they're used in the next.
for path in "${paths[@]}"; do
  [[ "$path" == *.py ]] || continue
  [[ "$path" = /* ]] || path="$repo_root/$path"
  [[ -f "$path" ]] || continue
  uv run ruff format "$path" >/dev/null 2>&1 || true
done

exit 0
