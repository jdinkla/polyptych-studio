#!/bin/bash
# PreToolUse hook: block Edit/Write to secrets-bearing files (.env, .envrc, ...).
# Receives the tool-call JSON on stdin; denies via exit code 2 + JSON decision.
set -euo pipefail

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')
filename=$(basename "$file_path")

# Block .env, .env.local, .envrc, etc. Allow .env.example templates through.
if [[ "$filename" == .env* && "$filename" != ".env.example" ]]; then
  jq -n --arg f "$filename" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("Refusing to edit secrets-bearing file: " + $f + ". Edit it manually if intended.")
    }
  }'
  exit 2
fi

exit 0
