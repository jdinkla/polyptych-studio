---
name: run-pipeline
description: Run a pipeline (or resume from a specific step) using the unified `just gen` target plus named presets
argument-hint: <pipeline> <source-file> <output-dir> [--provider provider] [--style style] [--from step] [--to step]
---

# Pipeline Execution — Run or Resume Pipelines

## Role

You translate agent-friendly arguments into a `just gen <pipeline> ...` invocation
with appropriate `--image-preset` / `--pipeline-preset` flags, then execute it.
You handle auto-resume, provider selection, and post-run status reporting.

## Arguments

Parse from `$ARGUMENTS`:
- **pipeline**: `deck` (slide) or `infographic`
- **source**: path to source markdown file
- **output-dir**: path to output directory
- **--provider** (optional): gemini (default for deck), openai, xai
- **--style** (optional): style preset path or name
- **--from** (optional): step to resume from
- **--to** (optional): step to stop at
- **--concurrent** (optional): number of parallel image threads (overrides preset)

If required arguments are missing, ask for them.

## Process

### Step 1: Resolve Auto-Resume

If `--from` is not specified and the output directory exists with partial outputs:

```bash
uv run polyptych validate $OUTPUT_DIR --json
```

Use the `next_step` from the result to determine where to resume. If empty/missing,
start from the beginning.

### Step 2: Pick Image + Pipeline Presets

The core call shape is always:

```bash
just gen <pipeline> <SOURCE> --output-dir <OUT> [--style <STYLE>] \
    --image-preset <NAME> [--pipeline-preset <NAME>] [extra flags...]
```

**Image presets** (defined in `image-presets.yaml`, reusable across pipelines):

| Preset | Provider / Size / Aspect | Best for |
|--------|-------------------------|----------|
| `gem` | gemini, 1K, 16:9 | slide decks, quick iterations |
| `gem-2k` | gemini, 2K, 16:9 | infographic (text legibility) |
| `openai-low` | openai, 1536x1024, low | first-pass exploration |
| `openai-medium` | openai, 1536x1024, medium | volume work |
| `openai-high` | openai, 1536x1024, high | text-heavy slides, infographic |
| `xai` | xai, 16:9 | xAI experiments |

**Pipeline presets** (defined in `pipeline-presets.yaml`, scoped per pipeline):

| Pipeline | Preset | What it sets |
|----------|--------|--------------|
| slide | `fast` | concurrent=10, producers=5 |
| infographic | `critique` | critique=true (one round; pass --critique-rounds N for more) |

### Step 3: Default Picker (provider → image preset)

Map pipeline + provider to the default presets:

| Pipeline | provider=gemini (default) | provider=openai | provider=xai |
|----------|--------------------------|-----------------|--------------|
| deck | `--image-preset gem --pipeline-preset fast` | `--image-preset openai-low --pipeline-preset fast` | `--image-preset xai` |
| infographic | `--image-preset gem-2k` | `--image-preset openai-high` | — |

### Step 4: Resolve Style

If `--style` is provided:
- Bare name (e.g., `ghibli`) → glob `prompts/style-transfer/*/<name>.md` (presets live in category subdirectories like `anime/`, `editorial/`, `noir/`); if zero or multiple matches, list the candidates and ask
- Already a path → use as-is
- Not provided → check `manifest.yaml` in the output dir for the previously used style

For infographic, the default style is `prompts/style-transfer/infographic/semi-flat-vector.md`.

### Step 5: Build & Execute

Compose the command:

```bash
just gen deck sources/essay.md --output-dir generated/essay \
    --style prompts/style-transfer/editorial/painterly.md \
    --image-preset gem --pipeline-preset fast
```

For `--from` / `--to` / `--slides`, append directly — the
`gen` target is a passthrough:

```bash
just gen deck sources/x.md --output-dir generated/x \
    --style prompts/style-transfer/editorial/scholarly-monograph.md \
    --image-preset openai-low --pipeline-preset fast \
    --from images --slides 12,15
```

Common error patterns:
- `Error: Unknown image preset 'foo'` — typo; the message includes a "did you mean" suggestion
- `Error: Source file not found` — wrong source path
- `ContentBlockedError` — content safety filter, may need prompt adjustment
- `APIError` / `429` — rate limiting, suggest reducing concurrency
- `ValidationError` — corrupted intermediate output, suggest `--force` or manual fix

### Step 6: Post-Run Status

```bash
uv run polyptych validate $OUTPUT_DIR --json
```

Report which tasks completed, any validation failures, image count vs expected,
and the suggested next action.

## Notes

- Explicit CLI flags always beat presets, so `--quality high --image-preset openai-low`
  yields openai @ high (not low).
- Pipeline presets and image presets set disjoint key sets (pipeline behavior vs. image settings), so the two never conflict with each other.
- Boolean flags from presets are additive only — a preset can enable `--critique`,
  not disable a flag the user passed.
- The legacy per-variant just targets (`polyptych-gem`, `polyptych-low`, etc.) have
  been removed; everything routes through `gen` now.
