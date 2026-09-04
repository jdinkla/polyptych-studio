#!/bin/bash
# PreToolUse hook: block Edit/Write to secrets-bearing files (.env, .envrc, ...).
# Supports Claude Code's file_path input and Codex's apply_patch command input.
# Denies via exit code 2 plus a JSON decision understood by both agents.
set -euo pipefail

input=$(cat)

paths=()
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')
[[ -n "$file_path" ]] && paths+=("$file_path")

# Codex exposes an apply_patch call as tool_input.command. Extract every path
# named by an Add/Update/Delete directive so multi-file patches are covered.
while IFS= read -r patch_path; do
  [[ -n "$patch_path" ]] && paths+=("$patch_path")
done < <(
  printf '%s' "$input" |
    jq -r '.tool_input.command // empty' |
    sed -nE \
      -e 's/^\*\*\* (Add|Update|Delete) File: //p' \
      -e 's/^\*\*\* Move to: //p'
)

for path in "${paths[@]}"; do
  filename=$(basename "$path")

  # Block .env, .env.local, .envrc, etc. Allow committed example templates.
  if [[ "$filename" == .env* && "$filename" != *.example ]]; then
    jq -n --arg f "$filename" '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: ("Refusing to edit secrets-bearing file: " + $f + ". Edit it manually if intended.")
      }
    }'
    exit 2
  fi
done

exit 0
