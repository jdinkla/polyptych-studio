---
name: infographic
description: Generate a complete infographic from a source essay — text tasks run locally (zero API cost), images via the chosen image preset (default openai-low)
argument-hint: <source-file> [style] [image-preset]
---

# Infographic — One-Shot Pipeline

## Role

You run the full infographic pipeline end-to-end: generate i0/i1/i2 locally (you are the LLM), then run image generation via the chosen image preset's provider (default preset `openai-low` → OpenAI). The user types one command, you handle everything.

## Arguments

Parse from `$ARGUMENTS`:
- **source-file** (required): Path to the source markdown essay (e.g., `sources/frankfurt-1985.md`)
- **style** (optional): Style preset name or path. Default: `prompts/style-transfer/infographic/semi-flat-vector.md`
- **image-preset** (optional): Image preset name from `image-presets.yaml` (e.g., `openai-low`, `openai-high`, `gem`, `gem-2k`). Default: `openai-low`

If source-file is missing, ask for it.

## Derived Values

- **Output dir**: Derived from the source filename **and the style name**, so different styles never overwrite each other. Resolve the style first (see below), then strip the source's directory and extension, append `-infographic-<style-name>/`, and place in `generated/`. `<style-name>` is the style preset's basename without extension (the default `semi-flat-vector.md` → `semi-flat-vector`). Examples: `sources/frankfurt-1985.md` with the default style → `generated/frankfurt-1985-infographic-semi-flat-vector/`; with `--style dark-dashboard` → `generated/frankfurt-1985-infographic-dark-dashboard/`. An explicit `--output-dir` passed in `$ARGUMENTS` overrides this derivation entirely.
- **Style**: If a bare name is given (e.g., `dark-dashboard`), resolve to `prompts/style-transfer/infographic/<name>.md`. If a path is given, use as-is. If omitted, use `prompts/style-transfer/infographic/semi-flat-vector.md`.
- **Image preset**: If omitted, use `openai-low`. Otherwise use the supplied preset name as-is (must exist in `image-presets.yaml`).
- **Variants**: 1 (skill default; pass `--variants N` through `$ARGUMENTS` to override). This applies both to the i2 prompt variants and to image generation in Step 5.

## Process

### Step 1: Setup

1. Parse arguments and resolve the style path **first**, then derive the output dir from the source filename + style name (an explicit `--output-dir` overrides)
2. Verify the source file exists (read it)
3. Verify the style file exists (read it)
4. Look up the image preset in `image-presets.yaml` and note its **provider** and **quality** — needed in Step 4 (provider best-practices doc, text-density calibration). Gemini/xAI presets define no quality key; in that case the template's "no tier given" fallback applies
5. Create the output directory: `mkdir -p $OUTPUT_DIR`

### Step 2: Run i0 Locally (Content Analysis)

Execute i0 using the `/run-local-task` process:

1. Read the prompt template: `prompts/tasks/task-i0-analysis.md`
2. Read the task implementation: `src/polyptych/tasks/task_i0_analysis.py`
3. Read the Pydantic model: find `TaskI0Output` in `src/polyptych/models.py`
4. Read the source essay
5. Derive **real** paragraph numbers for `source_paragraphs`: paragraphs are the blank-line-separated blocks of the source, 1-indexed — the same split `number_paragraphs()` in `src/polyptych/text_utils.py` uses (`re.split(r"\n\s*\n", text.strip())`). Never invent plausible-looking numbers; `/trace-prompt` relies on them. If unsure, generate a numbered copy to count against: `uv run python -c "from polyptych.text_utils import number_paragraphs; import pathlib; print(number_paragraphs(pathlib.Path('$SOURCE').read_text()))" > /tmp/numbered-source.txt`
6. Generate YAML output conforming to `TaskI0Output`
7. Write to `$OUTPUT_DIR/task-i0-analysis.yaml`
8. Validate: `uv run polyptych validate $OUTPUT_DIR i0`
9. If validation fails, fix and retry

### Step 3: Run i1 Locally (Design Specification)

Execute i1 using the `/run-local-task` process:

1. Read the prompt template: `prompts/tasks/task-i1-design.md`
2. Read the task implementation: `src/polyptych/tasks/task_i1_design.py`
3. Read the Pydantic model: find `TaskI1Output` in `src/polyptych/models.py`
4. Read i0 output from `$OUTPUT_DIR/task-i0-analysis.yaml`
5. Read the source essay
6. Read the style preset file (already read in Step 1) and **align the design with it**: pick the `visual_style` closest to the preset's aesthetic and derive `color_palette` from the preset's stated colors — i2 applies the preset to the final image, so a conflicting palette here produces contradictory directives downstream
7. Generate YAML output conforming to `TaskI1Output`
8. Write to `$OUTPUT_DIR/task-i1-design.yaml`
9. Validate: `uv run polyptych validate $OUTPUT_DIR i1`
10. If validation fails, fix and retry

### Step 4: Run i2 Locally (Image Prompts)

Execute i2 using the `/run-local-task` process:

1. Read the prompt template: `prompts/tasks/task-i2-prompts.md`
2. Read the task implementation: `src/polyptych/tasks/task_i2_prompts.py`
3. Read the Pydantic model: find `TaskI2Output` in `src/polyptych/models.py`
4. Read the provider best-practices doc for the preset's provider (from Step 1): `prompts/providers/<provider>-best-practices.md` — the real i2 injects this into its system prompt, so apply it here too
5. Read i0 output from `$OUTPUT_DIR/task-i0-analysis.yaml`
6. Read i1 output from `$OUTPUT_DIR/task-i1-design.yaml`
7. Read the style preset file
8. Read the source essay
9. Generate YAML output conforming to `TaskI2Output` — emit exactly 1 prompt variant (per the skill default). **Calibrate in-image text density to the preset's quality tier** (from Step 1) per the template's "Calibrating Text Density to the Quality Tier" section — at `low`, keep only the title, section headers, and a few large labels
10. Write to `$OUTPUT_DIR/task-i2-prompts.yaml`
11. Validate: `uv run polyptych validate $OUTPUT_DIR i2`
12. If validation fails, fix and retry

### Step 4.5: Critique i2 Locally (Prompt Audit)

Before spending money on images, audit your own i2 output with **fresh eyes** — the generator (you, in Step 4) had all the information and can still ship defects a re-read catches. This step is local and free.

1. Read the critique rubric: `prompts/tasks/task-i2-critique.md`
2. Re-read `$OUTPUT_DIR/task-i0-analysis.yaml`, `$OUTPUT_DIR/task-i1-design.yaml`, and `$OUTPUT_DIR/task-i2-prompts.yaml` **from the files** (not from memory of writing them)
3. Apply all seven rubric checks. The three highest-yield ones, from real failures:
   - **Entity/color consistency**: every entity that appears in multiple sections of the prompt keeps the same fill color and treatment
   - **Trim-induced semantic loss**: after quality-tier text trimming, every visual element still communicates its i1 `content_summary` (no arrows converging from unlabeled nothing, no "three factors" visual with zero factors)
   - **Key-content coverage**: every i0 `primary` key point and the most striking `visualizable_data` items (especially numbers) survive in the prompt — if something had to go for the tier budget, the weakest content goes, not the strongest
4. If you find **critical or important** issues, fix `$OUTPUT_DIR/task-i2-prompts.yaml` directly (you are also the refiner — follow `prompts/tasks/task-i2-refine.md`: fix flagged material, preserve unflagged material, respect the tier's text budget), then re-validate: `uv run polyptych validate $OUTPUT_DIR i2`
5. Mention in the final report what the critique found and fixed (or that it was clean)

The CLI equivalent is `--critique` / `--pipeline-preset critique` on `polyptych infographic` (external LLM calls); in skill mode you always run this step because it costs nothing.

### Step 4.6: Write manifest.yaml

Before image generation, write `$OUTPUT_DIR/manifest.yaml` recording the local text-task run (field template in the run-local-pipeline skill, Step 4): `pipeline: infographic`, `mode: local`, `timestamp` (UTC ISO-8601), `git_commit` (short hash), `source` (basename), `models: claude-local`, `style_prompt` (resolved style path), `tasks_completed: [i0, i1, i2]`. The CLI image run in Step 5 overwrites it with the full CLI manifest (provider/size/quality) — that's expected; this manifest covers the case where Step 5 is skipped or fails, so review skills aren't blind.

### Step 5: Generate Images

Run image generation externally using the just target:

```bash
just gen infographic $SOURCE --output-dir $OUTPUT_DIR --style $STYLE --image-preset $IMAGE_PRESET --variants 1 --from images
```

This calls the configured image provider (from `$IMAGE_PRESET`, default `openai-low`) to generate the infographic images based on the i2 prompts.

### Step 6: Report

After completion, report:
- Output directory path
- Summary of each task (i0 analysis highlights, i1 design choices, i2 prompt count)
- Number of images generated (check `$OUTPUT_DIR/images/`)
- Suggest `/review-regen $OUTPUT_DIR` if the user wants to review image quality

## Error Handling

- **Validation failure on i0/i1/i2**: Read the error, fix the YAML, re-validate. Up to 3 attempts per task.
- **Image generation failure**: Report the error and suggest:
  ```
  /run-pipeline infographic $SOURCE $OUTPUT_DIR --from images
  ```
- **Source file not found**: Ask the user for the correct path
- **Style file not found**: List available styles from `prompts/style-transfer/infographic/` and ask the user to pick one

## Notes

- The local task process (Steps 2-4.5) follows the same procedure as `/run-local-task` — read prompt template, task implementation, Pydantic model, dependencies, then generate conforming YAML. Refer to the run-local-task skill for the detailed generation process.
- All text tasks (i0, i1, i2, and the i2 critique) are well-suited for local execution — they are structured, schema-driven, and have shorter reasoning chains.
- The only external API cost is image generation in Step 5.
- **Generalized equivalent:** `/run-local-pipeline infographic` runs the same text tasks (i0→i1→i2) but stops before image generation. Use this skill (`/infographic`) when you want the full end-to-end flow including images; use `/run-local-pipeline infographic` when you only need the text tasks.
