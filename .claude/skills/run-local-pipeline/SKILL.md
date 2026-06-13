---
name: run-local-pipeline
description: Run all text tasks of any pipeline locally (Claude generates YAML instead of calling external LLMs), stopping before image generation
argument-hint: <pipeline> <source-file> [output-dir] [--style <preset>] [--critique] [--qa]
---

# Local Pipeline — Full Text Pipeline Execution

## Role

You run all text tasks of a pipeline locally, generating YAML outputs conforming to Pydantic schemas. Only image generation requires external APIs. This generalizes the `/infographic` skill to both pipelines.

## Arguments

Parse from `$ARGUMENTS`:
- **pipeline** (required): `slide` | `infographic`
- **source-file** (required): Path to the source markdown essay
- **output-dir** (optional): Defaults to `generated/<source-basename>-<pipeline>`
- **--style** (optional): Visual style preset name or path. Bare names resolve to `prompts/style-transfer/<category>/<name>.md`. Used by image prompt tasks (task7, i2) and by the design tasks (task5, i1), which align their palette and visual style with the preset.
- **--critique** (optional): Infographic only. Run the i2 self-critique/refine pass (`i2_critique` → `i2_refine`) before stopping. Off by default; in skill mode it costs nothing, so prefer running it.
- **--qa** (optional): QA mode. Emit the suggested image-generation command after text tasks complete so the user can review YAML before paying for images. Off by default — pipelines run unattended end-to-end (per `CLAUDE.md`), so a routine handoff suggestion is noise.

If pipeline or source-file is missing, ask for them.

## Pipeline Text Task DAGs

These are the text tasks to run locally, in dependency order. Tasks at the same depth with no cross-dependencies can run in parallel (via sequential `/run-local-task` calls in practice).

### slide
```
task1 → task2 → task3 → task4 → task5 → task6 → task7
```
Dependencies:
- task1: [] (source only)
- task2: [task1]
- task3: [task1, task2]
- task4: [task1, task2, task3]
- task5: [task1, task2, task4]
- task6: [task1, task2, task3, task4, task5]
- task7: [task1, task5, task6]

Image handoff: `just gen deck $SOURCE --output-dir $OUTPUT_DIR --style $STYLE --image-preset gem --pipeline-preset fast --from images`

### infographic
```
i0 → i1 → i2  (→ i2_critique → i2_refine, when --critique)
```
Dependencies:
- i0: [] (source only)
- i1: [i0]
- i2: [i0, i1]

When `--critique` is set, run the self-audit/refine pass after i2 (see the `/infographic` skill, "Critique i2 Locally"): re-read i0/i1/i2 from disk, apply `prompts/tasks/task-i2-critique.md`, and fix `task-i2-prompts.yaml` in place per `prompts/tasks/task-i2-refine.md`, then re-validate i2.

Image handoff: `just gen infographic $SOURCE --output-dir $OUTPUT_DIR --style $STYLE --image-preset openai-low --from images` (matches the `/infographic` skill default; use `gem-2k` or `openai-high` as a quality upgrade)

## Task Registry

Reuses the complete task registry from `/run-local-task`. See that skill for the full mapping of each task to its prompt file, Pydantic model class, output file, and dependencies.

### Quick Reference — Output Files

| Pipeline | Tasks → Output Files |
|----------|---------------------|
| **slide** | task1→`task1-genre.yaml`, task2→`task2-analysis.yaml`, task3→`task3-structure.yaml`, task4→`task4-content.yaml`, task5→`task5-design.yaml`, task6→`task6-slides.yaml`, task7→`task7-prompts.yaml` |
| **infographic** | i0→`task-i0-analysis.yaml`, i1→`task-i1-design.yaml`, i2→`task-i2-prompts.yaml` |

## Process

### Step 1: Setup

1. Parse arguments, validate pipeline name
2. Derive output directory if not provided: `generated/<source-basename>-<pipeline>`
   - Example: `sources/frankfurt-1985.md` + `infographic` → `generated/frankfurt-1985-infographic/`
3. Verify the source file exists (read it)
4. If `--style` provided, resolve the style file path:
   - Bare name → glob `prompts/style-transfer/*/<name>.md` (presets live in category subdirectories like `anime/`, `editorial/`, `infographic/`, `noir/`, `period-art/`); for infographic prefer `prompts/style-transfer/infographic/<name>.md`. If zero or multiple matches, list the candidates and ask.
   - Full path → use as-is
5. Create output directory: `mkdir -p $OUTPUT_DIR`
6. Copy source file to output directory if not already there: `cp $SOURCE $OUTPUT_DIR/source.md`

### Step 2: Determine Task Execution Order

Both pipelines are linear — follow the sequence:
- slide: task1 → task2 → ... → task7
- infographic: i0 → i1 → i2 (then i2_critique → i2_refine when `--critique`)

### Step 3: Execute Each Text Task

For each task in execution order:

#### 3a: Check for Resume (Skip Existing Valid Outputs)

Check if the task's output file already exists in the output directory:
```bash
uv run polyptych validate $OUTPUT_DIR $TASK_NAME
```
If validation passes, **skip this task** — it's already done. Report "Skipping $TASK_NAME — valid output exists" and move to the next task.

#### 3b: Execute the Task via /run-local-task Process

Follow the exact process defined in the `/run-local-task` skill:

1. **Read the prompt template** from `prompts/tasks/<prompt-file>.md`
2. **Read the task implementation** from `src/polyptych/tasks/task_*.py` to understand context assembly
3. **Read the Pydantic model** from `src/polyptych/models.py` for the exact schema
4. **Read dependency outputs** from disk (per the DAG)
5. **Read the source essay** from the output directory
6. **Generate YAML** conforming to the schema
7. **Write** to `$OUTPUT_DIR/<output-file>`
8. **Validate** with `uv run polyptych validate $OUTPUT_DIR $TASK_NAME`
9. **Retry once** on validation failure — read the error, fix the YAML, re-validate

### Step 4: Write manifest.yaml

After the text tasks complete, write `$OUTPUT_DIR/manifest.yaml` so review skills (`/check-status`, `/review-regen`, `/trace-prompt`) and later CLI resumes know how this directory was produced. Use the same field names as the CLI-written manifest where the concept overlaps:

```yaml
pipeline: <internal pipeline name>        # slide | infographic
mode: local                               # marks a skill-mode run (CLI manifests have no mode field)
timestamp: <UTC ISO-8601>                 # date -u +%Y-%m-%dT%H:%M:%S+00:00
git_commit: <short hash>                  # git rev-parse --short HEAD
source: <source file basename>            # e.g. essay.md (matches CLI: name only)
models: claude-local                      # Claude generated the task YAML locally
style_prompt: <path passed via --style>   # omit if no style was used
tasks_completed: [task1, task2, ...]      # text tasks that exist and validate
```

Rules:
- Omit keys with no value (the CLI strips `None` values the same way).
- If a manifest already exists (partial earlier run), update `timestamp`, `git_commit`, and `tasks_completed`; preserve other fields unless this run changed them (e.g. a different `--style`).
- A later CLI resume (`--from images`) overwrites this file with the full CLI manifest (image provider/size/quality etc.) — that is expected and fine; the local manifest's job is to cover the gap until then.

### Step 5: Report

After all text tasks complete:
1. Summarize what was generated (task count, key outputs)
2. List any tasks that were skipped (resume)
3. **Only if `--qa` was passed**: suggest the image-generation command from the "Image handoff" section of the pipeline DAG above. Otherwise omit it — pipelines run unattended end-to-end and a routine handoff line is noise.
4. Mention that individual tasks can be re-run with `/run-local-task` or externally with `/run-pipeline --from <task>`

The per-pipeline "Image handoff" commands documented in the DAG sections are reference material for `--qa` mode (and for the user when they decide to proceed manually). They are not emitted by default.

## Special Cases

### 1. Task 6 — Genre-Specific Prompts (Slide Pipeline)

Task 6 loads a genre-specific prompt variant based on the genre from task1 output:
- Base prompt: `prompts/tasks/task-06-slide-specification.md`
- If genre is `fiction`: tries `prompts/tasks/task-06-slide-specification-fiction.md` first
- Falls back to base if the variant file doesn't exist

**You must read the task1 output first** to determine the genre, then load the correct prompt file.

### 2. Style Preset Injection

For the final prompt-generation task of each pipeline (task7, i2), if a `--style` preset was provided:
- Read the style file
- Inject its content as additional context when generating the image prompts
- Read the task implementation to see exactly where/how style content is incorporated

The design tasks (task5, i1) also receive the preset: derive their color palette and visual style from the preset's stated aesthetic instead of inventing one, so the design spec and the final style transfer don't contradict each other.

### 3. Fiction Character Canon (Slide Pipeline)

When task1 classifies the source as `fiction`:

- **task2** must emit `character_canon` — one canonical visual description per recurring character (fields: `name`, `age`, `face`, `hair`, `build`, `costume`, `distinguishing`). See the Character Canon section of `prompts/tasks/task-02-source-analysis.md`. Invent stable, concrete details where the source is silent.
- **task6**: every `characters_in_frame` entry must start with the exact canonical `name` (parenthetical position/state allowed).
- **task7**: embed each in-frame character's canonical description verbatim in the slide prompt's CONSISTENCY section — identical string on every slide featuring that character. The canonical line format is `<name>: <age>; <face>; <hair>; <build>; <costume>[; <distinguishing>]` (matches `CharacterSheet.identity_lock_line()` in `src/polyptych/models/slide.py`).

Non-fiction sources: omit `character_canon` entirely.

### 4. Provider Tuning for Image-Prompt Tasks

The CLI versions of the prompt-generation tasks (task7, i2) inject `prompts/providers/<provider>-best-practices.md` into the LLM context so the prompts play to the image provider's strengths. Replicate this locally:

1. Determine the target image provider: an explicit provider/image-preset stated by the user > the provider implied by the pipeline's image-handoff default above (`gem`/`gem-2k` → gemini; `openai-*` → openai; `xai` → xai).
2. Read `prompts/providers/<provider>-best-practices.md` and apply its guidance when writing the image prompts.
3. **task7 only**: set the top-level `prompt_provider: <provider>` field in `task7-prompts.yaml`. The pipeline records this field on CLI runs too, and warns at image time when images are generated with a different provider (the warning suggests re-running task7 to retune the prompts).

## Error Handling

- **Validation failure**: Read the error, fix the YAML, re-validate. Up to 2 attempts per task. If still failing after 2 retries, report the error and stop — don't continue to dependent tasks.
- **Missing source file**: Ask the user for the correct path.
- **Missing dependency output**: This shouldn't happen since we execute in DAG order, but if a dependency file is missing (e.g., corrupted), report it and stop.
- **Invalid pipeline name**: List the two valid pipeline names (`slide`, `infographic`) and ask again.

## Examples

### Full slide pipeline
```
/run-local-pipeline slide sources/my-essay.md
```
Generates task1 through task7 in `generated/my-essay-slide/` and reports completion. No image-handoff line is emitted by default.

### QA-mode slide pipeline
```
/run-local-pipeline slide sources/my-essay.md --qa
```
Generates the same text tasks, then additionally suggests the image-generation command so the user can review YAML before paying for images:
```
just gen deck sources/my-essay.md --output-dir generated/my-essay-slide/ --style prompts/style-transfer/editorial/scholarly-monograph.md --image-preset gem --pipeline-preset fast --from images
```

### Infographic with style and critique
```
/run-local-pipeline infographic sources/essay.md --style semi-flat-vector --critique
```
Runs i0 → i1 → i2 → i2 critique/refine in `generated/essay-infographic/`. (Use `/infographic` instead if you also want images generated.)

### Resume after partial run
```
/run-local-pipeline slide sources/essay.md generated/essay-slide
```
If task1–task4 already exist and validate, skips them and starts from task5.

## Notes

- This skill follows the exact same per-task process as `/run-local-task` — it just chains the tasks automatically based on the pipeline DAG.
- The `/infographic` skill is a specialized equivalent of `/run-local-pipeline infographic` that also runs image generation. Use `/infographic` if you want images included; use `/run-local-pipeline infographic` if you only want the text tasks.
- For image generation after text tasks, use the suggested `just` command or `/run-pipeline <pipeline> $SOURCE $OUTPUT_DIR --from images`.
- All text tasks are well within Claude's capabilities. The batched task A1 is the most demanding due to length, but generating it in a single pass avoids the complexity of batch merging.
