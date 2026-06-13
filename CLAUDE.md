# CLAUDE.md

## Project Purpose

This project is an **essay-to-visuals generation system** with two independent
pipelines — **slide** (a sectioned slide deck) and **infographic** (a
single-page infographic) — backed by multi-provider text generation with a
fallback chain (Gemini, OpenAI, xAI, Anthropic, Vertex AI) and multi-provider
image generation (Gemini, OpenAI, xAI, Vertex AI via the `pixbridge` package).

## Project Structure

```
src/
  common/                    # Shared utilities (usage logging)
  polyptych/                 # Pipelines (slide tasks 1-7, infographic i0-i2)
prompts/
  tasks/                     # Task prompt templates (task-01..task-07, task-i0..task-i2, task-critique)
  style-transfer/            # Example visual style presets (anime, editorial, infographic, noir, period-art)
  providers/                 # Provider-specific best practices (gemini, openai, xai)
model_config.yaml            # Per-task LLM model tier configuration
image_model_config.yaml      # Per-provider image generation model configuration
image-presets.yaml           # Reusable image-generation presets (provider/size/aspect/quality bundles)
pipeline-presets.yaml        # Pipeline-specific behavior presets (concurrency, ...)
docs/                        # Architecture, reference, how-to docs
justfile                     # Common workflow shortcuts
```

## CLI Tool

One CLI entry point: `polyptych`, with subcommands `deck` (slide), `infographic`,
`validate`, and `clean-source`.

For detailed subcommands, flags, pipeline task tables, environment variables,
output structure, and just targets, see **[docs/reference/cli-reference.md](docs/reference/cli-reference.md)**.

## Development

```bash
uv sync                                 # Install dependencies
uv run polyptych deck source.md         # Run full slide deck pipeline
uv run polyptych infographic source.md  # Run infographic pipeline
just --list                             # Show all just targets
```

Per-task model selection is configured in `model_config.yaml`. Resolution order:
`--model` flag > `$POLYPTYCH_MODEL` env var (deprecated alias `$SLIDE_GEN_MODEL`)
> config tiers.

### Cross-repo editing (pixbridge)

The `pixbridge` package (image generation; import module `pixbridge`) is a
normal PyPI dependency — no `[tool.uv.sources]` entry. A normal `uv run`
resyncs the venv on every invocation, **clobbering any
`uv pip install -e ../pixbridge` editable install** with the PyPI version.

To test against local edits in a sibling `pixbridge` checkout:

1. Install local editable: `uv pip install -e ../pixbridge --reinstall`
2. Run with both flag and env var: `UV_NO_SYNC=1 uv run --no-sync pytest ...`
   — `--no-sync` alone isn't enough because something else still triggers a
   resync in some commands.

Alternative: temporarily add a `[tool.uv.sources]` override
`pixbridge = { path = "../pixbridge", editable = true }` and `uv sync`. Revert
before committing.

### Image-generation flags (common to both pipelines)

Both image-producing subcommands (`deck`, `infographic`) accept the same
image-generation flag set:

- `--image-preset NAME` — apply a named bundle from `image-presets.yaml`
  (provider/size/aspect-ratio/quality). Available: `gem`, `gem-2k`,
  `openai-low`, `openai-medium`, `openai-high`, `xai`
- `--pipeline-preset NAME` — apply a named bundle from
  `pipeline-presets.yaml[<pipeline>]` (concurrency + pipeline-specific flags).
  Examples: `slide/fast`, `infographic/critique`
- `--provider {gemini,openai,xai,vertex}` — image provider. Default `gemini`.
- `--image-model` — override the image model; resolution: `--image-model` >
  `$POLYPTYCH_IMAGE_MODEL` (deprecated alias `$SLIDE_GEN_IMAGE_MODEL`) >
  `image_model_config.yaml` > provider built-in
- `--size` — output size. OpenAI gpt-image-2: any `WxH` divisible by 16, aspect
  ratio in `[1:3, 3:1]`, `max(W, H) ≤ 3840` (e.g. `1024x1024`, `1536x1024`,
  `2048x1152`). Gemini: `1K` / `2K`. Invalid sizes raise a clear error.
- `--aspect-ratio {16:9,4:3,3:4,9:16,1:1}` — default `16:9`
- `--quality {low,medium,high,auto}` — OpenAI gpt-image-2 only; defaults to
  `high` for both slide and infographic
- `--ref-image PATH` (repeatable) — reference image applied to every generated
  image; requires a provider that supports references (`openai`, `gemini`)
- `--output-format {png,jpeg,webp}` / `--compression N` — OpenAI gpt-image-2 only
- `--style PATH` — path to a style-transfer markdown preset. If a sibling image
  (`<name>.png/.jpg/.jpeg/.webp`) exists next to the `.md`, it is auto-prepended
  to the reference list (providers supporting refs only)

**Resolution order** (highest wins): explicit CLI flag > `--pipeline-preset` >
`--image-preset` > per-pipeline defaults > built-ins.

## Workflow: use `just gen`

Prefer the unified `just gen <pipeline> ...` target over raw `uv run`:

```bash
just gen infographic sources/x.md --output-dir generated/x \
    --style prompts/style-transfer/infographic/semi-flat-vector.md \
    --image-preset openai-low
```

Run `just --list` for the full target list. See
[docs/reference/cli-reference.md](docs/reference/cli-reference.md) for details.

## Use Context7 by Default

Always use Context7 when code generation, setup or configuration steps, or
library/API documentation is needed — use the Context7 MCP tools to resolve
library IDs and get library docs without requiring explicit user requests.

## Agent Skills — Autonomous Pipeline Operation

Skills enable Claude Code to operate the pipelines autonomously. They live in
`.claude/skills/` and are invoked as slash commands.

**Run / orchestrate**

| Skill | Command | Purpose |
|-------|---------|---------|
| `run-pipeline` | `/run-pipeline <pipeline> <source> <output-dir> [flags]` | Execute or resume a pipeline via the correct `just` target |
| `run-local-pipeline` | `/run-local-pipeline <pipeline> <source> [output-dir] [flags]` | Run all text tasks locally (Claude generates YAML), stopping before image generation |
| `run-local-task` | `/run-local-task <task-name> <output-dir> [--source file]` | Execute a single task locally |
| `infographic` | `/infographic <source-file> [style] [image-preset]` | One-shot infographic: runs i0–i2 locally (zero API cost), then images |

**Inspect, review, iterate**

| Skill | Command | Purpose |
|-------|---------|---------|
| `check-status` | `/check-status <output-dir>` | Report which tasks are done, what's next |
| `review-regen` | `/review-regen <output-dir>` | Review images, identify issues, build selective regeneration commands |
| `trace-prompt` | `/trace-prompt <output-dir> <item-number>` | Trace an image back through the pipeline to find a visual issue's origin |
| `edit-output` | `/edit-output <output-dir> <task-name> <changes>` | Modify task YAML, validate, identify downstream tasks |

**Authoring & analysis helpers**

| Skill | Command | Purpose |
|-------|---------|---------|
| `clean-source` | `/clean-source <input-file> [flags]` | Clean PDF-converted markdown |
| `suggest-style` | `/suggest-style <source-file>` | Recommend a style-transfer preset (or propose a new one) |
| `new-style` | `/new-style <name> <brief>` | Create a new visual style transfer preset |
| `qa-test` | `/qa-test <package-name>` | Analyze test coverage gaps and write missing tests |
| `check-models` | `/check-models <provider>` | Search the web for the latest model identifiers and compare with config |

For the conceptual relationship between skill mode and the Python CLI, see
[docs/explanation/operating-modes.md](docs/explanation/operating-modes.md).

### Execution conventions

**Pipelines run unattended end-to-end.** The pipeline skills are designed to
produce a finished artifact in one shot. Do not insert a human checkpoint
between text tasks (i0/i1/i2, task1..task7) and image generation as a routine
matter — interception is the exception, reserved for QA-style development.

Cost-control decisions belong **upfront** (pick the right `--image-preset`,
`--variants`, style). Recovery from bad outputs happens **after the run** via
`/review-regen`, `/edit-output`, or re-running with adjusted flags.

**Prefer local for development.** When developing/iterating on the pipelines
(prompt edits, post-processing, validators), prefer the local skills —
`/run-local-pipeline`, `/run-local-task`, `/infographic` (text tasks) — over
external LLM/image APIs. Local runs let Claude generate the task YAML directly,
so they cost nothing. Reach for the external-API path only when the work
requires it (final image generation, provider-specific behavior).

**Default providers when a real run is required.** Use **`gemini` for text** and
**`--image-preset openai-low` for images** unless told otherwise — the cheapest
combination that still exercises the real APIs.

### Reviewing generated outputs

Every pipeline writes `manifest.yaml` to its output dir capturing the resolved
run configuration: `image_provider`, `image_quality`, `image_size`,
`aspect_ratio`, `style_prompt`, `from_step`/`to_step`, `num_variants`, models,
git commit. **Always `Read` `manifest.yaml` before opening images or task
YAMLs** — the resolved settings (after argparse defaults and `just` preset
expansion) usually explain why an image looks the way it does, and they are not
recoverable from the user's command line alone. Cite the manifest's
quality/style values when explaining why an output looks the way it does.

Local skill runs (`/run-local-pipeline`, `/run-local-task`, `/infographic`)
write a compatible manifest too (`mode: local`, `models: claude-local`,
`tasks_completed`, plus the shared `pipeline`/`source`/`style_prompt`/
`git_commit` fields); a later CLI image run overwrites it with the full manifest.

### Validation CLI

`uv run polyptych validate <output-dir> [task-name] [--json]` — validates task
YAML outputs against Pydantic schemas. Used by skills for automated status
checking.

### Source Cleaning

`uv run polyptych clean-source <file> [--output <path>] [--dry-run]
[--keep-footnotes] [--keep-toc]` — strips PDF-to-markdown conversion artifacts
(page numbers, footnotes, TOC, broken image refs, backslash escaping). Use
before feeding PDF-converted sources into pipelines.

### Typical Agent Workflow

```
/run-local-pipeline slide sources/essay.md       # All slide text tasks locally, suggests image command
/infographic sources/essay.md                    # One-shot: i0-i2 locally + preset images (default openai-low)
/clean-source sources/thesis.md                  # Strip PDF artifacts before pipeline
/check-status generated/my-project               # What exists?
/run-local-task i0 generated/my-project --source essays/essay.md   # Run single task locally
/run-pipeline infographic essays/essay.md generated/my-project --from images   # External for images
/review-regen generated/my-project               # Review results
/edit-output generated/my-project i2 "improve prompt 3"            # Iterate
```
