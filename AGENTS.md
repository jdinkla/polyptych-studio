# Codex repository instructions

Before working in this repository, read `CLAUDE.md` completely. It is the
shared source of project architecture, development commands, pipeline
conventions, and operational safeguards; the filename is retained so Claude
Code and Codex can use the same maintained guidance.

## Codex compatibility

- Repository skills are exposed under `.agents/skills/` and share their source
  with `.claude/skills/`. In Codex, invoke them as `$run-pipeline`,
  `$run-local-pipeline`, `$run-local-task`, `$infographic`, `$check-status`,
  `$review-regen`, `$trace-prompt`, `$edit-output`, `$clean-source`,
  `$suggest-style`, `$new-style`, `$qa-test`, or `$check-models`.
- A slash-prefixed skill name in shared documentation means the same workflow;
  use Codex's `$skill-name` syntax when invoking it explicitly.
- The project-scoped `prompt_consistency_reviewer` custom agent is available
  for prompt/config audits when the user requests a specialist or parallel
  review. Do not delegate ordinary edits merely because the agent exists.
- Project hooks protect secrets-bearing `.env*` files and format Python files
  changed through patch tools. Codex requires each contributor to review and
  trust repository hooks before they run.
- Codex command shells are non-interactive and may not receive the variables
  that an interactive terminal loads through `direnv`. For credentialed
  pipeline commands, use `direnv exec . <command>` so the repository's
  `.envrc` is evaluated explicitly. This `.envrc` retrieves secrets through
  GPG; if the sandbox cannot reach `~/.gnupg` or the GPG agent, rerun the
  credentialed command with the required sandbox escalation. Never display,
  log, or ask the user to paste secret values. A presence check such as
  `direnv exec . sh -c 'test -n "$OPENAI_API_KEY"'` is safe because it emits
  no value.
- The Context7 instruction in `CLAUDE.md` applies only when that MCP integration
  is available. Otherwise use available primary documentation sources.

## Verification

For Python changes, run the focused tests first, then the repository gates that
match the change. The complete local CI-equivalent set is:

```bash
just lint
just typecheck
just test
```

Integration tests and real pipeline/image runs require provider credentials,
can incur cost, and are opt-in unless the user explicitly asks for them.
