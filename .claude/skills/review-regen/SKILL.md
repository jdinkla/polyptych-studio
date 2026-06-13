---
name: review-regen
description: Review generated images in an output directory, identify quality issues, and build selective regeneration commands
argument-hint: <output-directory>
---

# Review Generated Output & Plan Selective Regeneration

## Role

You are a quality reviewer for AI-generated image pipelines. Your task is to review a generated output directory, identify images that need regeneration, and construct the correct `just` commands.

## Arguments

- `$ARGUMENTS` = path to the output directory (e.g., `generated/my-project`)

If no directory is provided, ask the user which output directory to review.

## Process

### Step 1: Detect Pipeline Type

Determine the pipeline type from files present in the directory:

| Pipeline | Detection Signal | Image Pattern | Regen Flag |
|----------|-----------------|---------------|------------|
| **Slide** | `task4-content.yaml` exists | `slide-NN.{jpg,png}` | `--slides` |
| **Infographic** | `task-i2-prompts.yaml` exists | `infographic-vN.{jpg,png}` | (rerun from i2) |

Check which task YAML files exist to identify the pipeline. Report the detected type.

### Step 2: Run Integrity Check

Run the automated integrity check:

```bash
uv run pixbridge check {directory}/images
```

Report any failures: corruption, excessive transparency, uniform bottom bands (truncation).

### Step 3: Visual Review

Read and display ALL images from `{directory}/images/` so you can inspect them visually.

For each image, assess:
- **Composition**: Is the framing coherent? Are subjects well-placed?
- **Style consistency**: Does it match the other images in the set?
- **Text artifacts**: Any garbled or hallucinated text in the image?
- **Anatomical issues**: Distorted hands, faces, proportions?
- **Truncation**: Image appears cut off or has fill bands at edges?
- **Prompt adherence**: Does the image match its prompt? (Read the corresponding prompt YAML from `{directory}/prompts/`)

### Step 4: Compile Report

Present findings as a table:

```
| # | Image | Status | Issues |
|---|-------|--------|--------|
| 1 | slide-01.jpg | OK | — |
| 2 | slide-02.jpg | REGEN | Garbled text, style drift |
| 3 | slide-03.jpg | OK | — |
```

### Step 5: Detect Style and Source

Read `{directory}/manifest.yaml` if it exists to find the style preset and source file used. Local skill runs write a manifest too (`mode: local`, `style_prompt`, `tasks_completed`) — the style that shaped the prompts is in `style_prompt` even when no CLI image run has happened yet.

Otherwise, check:
- `{directory}/source.md` for the source file
- Prompt files in `{directory}/prompts/` for style references

### Step 6: Build Regeneration Command

Based on flagged images and detected pipeline type, construct the `just` command.

**Template mapping** — all regeneration goes through `just gen <pipeline> ... --from images <selector>`. Pick an `--image-preset` per provider and append the selector flag for the pipeline:

| Pipeline | Selector flag | Image preset → flags |
|----------|---------------|----------------------|
| Slide (deck) | `--slides "NUMS"` | OpenAI: `--image-preset openai-low`, Gemini: `--image-preset gem`, xAI: `--image-preset xai` |
| Infographic | `--from i2` (no per-image selector) | Gemini: `--image-preset gem-2k`, OpenAI: `--image-preset openai-high` |

**Example regeneration commands** (replace `SOURCE`, `OUT`, `STYLE`, `NUMS`):

```bash
# Slide, Gemini, regen slides 3 and 5-7
just gen deck SOURCE --output-dir OUT --style STYLE --image-preset gem --from images --slides "3,5-7"

# Slide, OpenAI low quality, regen slide 4
just gen deck SOURCE --output-dir OUT --style STYLE --image-preset openai-low --from images --slides "4"

# Infographic, OpenAI high (re-run i2 → images)
just gen infographic SOURCE --output-dir OUT --style STYLE --image-preset openai-high --from i2
```

**Number format**: Comma-separated with ranges where consecutive (e.g., `"3,5,8-12,15"`).

**Ask the user:**
1. Which provider to use for regeneration (default: same as original if detectable)
2. Whether to regenerate all flagged images or a subset
3. Whether to try a different provider for problem images

### Step 7: Execute (with confirmation)

Present the complete `just` command and ask for confirmation before running.

If many images need regeneration (>30% of total), suggest re-running the full image step instead of selective regeneration.

## Notes

- Images are 1-indexed (slide-01; infographic variants are `infographic-v1`, `infographic-v2`, ...)
- The `--from images` flag is implicit in the selective regen just targets
- If the user wants to switch providers mid-run, the prompts are reusable — only the image generation step reruns
