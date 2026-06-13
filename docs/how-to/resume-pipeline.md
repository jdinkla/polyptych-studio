# Resume a Pipeline

How to resume a failed or interrupted pipeline, regenerate specific items, and check pipeline status.

## Auto-Resume

All pipelines support automatic resume. If a pipeline is interrupted, re-run the same command — it detects existing outputs and skips completed steps:

```bash
# First run (interrupted at task5)
uv run polyptych deck source.md -o generated/my-project

# Re-run — automatically resumes from task5
uv run polyptych deck source.md -o generated/my-project
```

The pipeline validates each step's YAML output against its Pydantic model. The first step with a missing or invalid output becomes the resume point.

## Resume from a Specific Step

Use `--from` to re-run from a particular step onwards. All upstream outputs must exist (or the pipeline errors on missing dependencies).

```bash
# Slide pipeline: resume from image generation (all text tasks already complete)
uv run polyptych deck source.md -o generated/my-project --from images

# Slide pipeline: re-run from content allocation onward
uv run polyptych deck source.md -o generated/my-project --from task4

# Infographic pipeline: re-run from prompt generation
uv run polyptych infographic source.md -o infographic_output/my-project --from i2
```

Note: `--from <step>` re-runs `<step>` and everything after it. To only re-run text tasks up to some step, combine with `--to <step>`.

## Selective Regeneration

Regenerate specific slides without re-running the full pipeline (slide pipeline only):

```bash
# Slides 3, 7, and 12
uv run polyptych deck source.md -o generated/my-project --from images --slides 3,7,12

# Slides 1-5
uv run polyptych deck source.md -o generated/my-project --from images --slides 1-5
```

The infographic pipeline regenerates all variants at once; use `--variants N` to change how many are produced.

## Check Pipeline Status

Use the validation CLI to see what's complete:

```bash
uv run polyptych validate generated/my-project
```

This checks each task output against its schema and reports which are valid, missing, or corrupt.

## Change Provider Mid-Run

You can switch providers when resuming. For example, generate text with Gemini but switch to OpenAI for images:

```bash
# Text tasks with Gemini (default)
uv run polyptych deck source.md -o generated/my-project --to task7

# Images with OpenAI
uv run polyptych deck source.md -o generated/my-project --from images \
  --provider openai --quality high
```

## Force Regeneration

To regenerate all items (ignoring existing files), use `--force` with `--concurrent`:

```bash
uv run polyptych deck source.md -o generated/my-project --from images \
  --concurrent 4 --force
```

## Related

- [CLI Reference](../reference/cli-reference.md) — full flag documentation
- [Write Style Prompts](write-style-prompts.md) — customize the visual style of generated images
