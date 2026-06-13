# Operating Modes: Python CLI vs Claude Code Skills

The system can be driven two ways:

1. **Python CLI mode** — you run `polyptych` directly (or via `just` targets). Pipelines call configured external LLMs and image providers per `model_config.yaml` and `image_model_config.yaml`.
2. **Claude Code skills mode** — inside a Claude Code session you type `/<skill>` slash commands. The agent orchestrates the work, can substitute itself for the LLM on text tasks, and can iterate on outputs.

Both modes target the same project, the same task templates under `prompts/tasks/`, the same Pydantic schemas, and the same `generated/<dir>/` output layout. Skill mode is **not** a replacement for the CLI — most skills shell out to it.

## Quick comparison

|  | Python CLI | Skills |
|---|---|---|
| Invocation | `uv run polyptych deck …` (or `just`) | `/run-pipeline …`, `/run-local-pipeline …`, `/infographic …` |
| Text-task LLM | Configured provider per `model_config.yaml` | Either the configured provider (`/run-pipeline`) **or** Claude itself (`/run-local-pipeline`, `/run-local-task`, `/infographic`) |
| Image generation | Configured provider | Same — skills delegate to the CLI |
| Reproducibility | Deterministic given source, config, seeds | Lower for text tasks generated locally — output reflects Claude's in-conversation reasoning |
| Cost | One API bill per text task + image generation | Zero API cost for text tasks run locally; image cost unchanged |
| Iteration | Hand-edit YAML, re-run with `--from <step>` | `/edit-output` proposes a change and replays downstream tasks |
| Debugging | Read logs, YAML, and `manifest.yaml` by hand | `/check-status`, `/review-regen`, `/trace-prompt` summarize state |

## When to use which

**Python CLI** is the right surface when:

- Running in CI, batch jobs, scripts, or `just` targets.
- You want determinism — same source, same config, same output.
- You're tuning prompt templates or `model_config.yaml` and want each result attributable to that config (not to Claude's in-conversation reasoning).
- You need a capability with no skill: `polyptych validate`.

**Skills** are the right surface when:

- You're exploring — drafting a style preset (`/new-style`), deciding what to fix.
- You want to skip the API for text tasks: `/run-local-pipeline`, `/run-local-task`, and `/infographic` have Claude generate the YAML directly. Image generation still hits the configured provider.
- You want guided review and iteration: `/check-status` to see what exists, `/review-regen` to plan regenerations, `/edit-output` to change one task and replay downstream, `/trace-prompt` to diagnose a bad image.
- You're authoring scaffolding — `/clean-source` strips PDF artifacts, `/qa-test` writes missing tests for a `src/` package.

The two modes mix freely. A typical agent flow:

```
/clean-source sources/essay.md                                    # strip PDF artifacts
/run-local-pipeline infographic sources/essay.md                  # text tasks via Claude (no API cost)
/run-pipeline infographic sources/essay.md generated/foo --from images   # CLI for images
/review-regen generated/foo                                       # review and plan regenerations
/edit-output generated/foo i2 "tighten prompt 3"                  # iterate
```

## Coverage map

The Python CLI is the larger surface. Skills are a curated layer over the workflows that benefit most from agent orchestration.

| Capability | Python CLI | Skill |
|---|---|---|
| Run a pipeline | `polyptych {deck,infographic}` | `/run-pipeline`, `/infographic` |
| Run text tasks locally (Claude as LLM) | — | `/run-local-pipeline`, `/run-local-task`, `/infographic` |
| Resume from a step | `--from <step>` | `/run-pipeline --from <step>` |
| Validate task YAML | `polyptych validate` | used internally by skills |
| Clean PDF source | `polyptych clean-source` | `/clean-source` |
| Author a style preset | hand-edit a markdown file | `/new-style` |
| Inspect output state | hand-read directory + `manifest.yaml` | `/check-status` |
| Review images, plan regen | hand | `/review-regen` |
| Trace image issues backwards | hand | `/trace-prompt` |
| Edit one task and replay downstream | hand-edit + `--from` | `/edit-output` |
| Write missing tests for a package | hand | `/qa-test` |
| Check provider for newer model IDs | hand | `/check-models` |

## See also

- [CLI Reference](../reference/cli-reference.md) — full Python CLI surface.
- [CLAUDE.md](../../CLAUDE.md) — canonical list of available skills.
