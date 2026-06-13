---
name: check-status
description: Check the current state of a pipeline output directory — which tasks are done, what's next, and key summary info
argument-hint: <output-directory>
---

# Pipeline Status — Situational Awareness

## Role

You are inspecting a pipeline output directory to understand its current state. Report what exists, what's valid, what's next, and key summary information.

## Arguments

- `$ARGUMENTS` = path to the output directory (e.g., `generated/my-project`)

If no directory is provided, ask the user which output directory to check.

## Process

### Step 1: Run Schema Validation

Run the validate command to check all task outputs:

```bash
uv run polyptych validate $ARGUMENTS --json
```

This will:
- Auto-detect the pipeline type from files present
- Validate each task YAML against its Pydantic schema
- Run cross-task referential checks when 2+ task files exist (slide pipeline: dangling scene_beat_ids, slide-count mismatches across task3/4/6/7, out-of-range paragraph references, unknown source_sections, arc peaks at nonexistent slides; headline/quote word limits as warnings) — findings appear under `cross_task` in the JSON
- Report the next step to run

Surface any `cross_task` errors prominently in the status report — they indicate broken references between task files even when every file is schema-valid.

If the directory doesn't exist or is empty, report that and stop.

### Step 2: Read the Manifest

If `$ARGUMENTS/manifest.yaml` exists, read it to extract:
- Source file path
- Style preset used
- Image provider and model
- Timestamp
- `mode: local` — the directory was produced by a local skill run (`/run-local-pipeline`, `/run-local-task`, `/infographic`): text-task YAMLs were Claude-generated (`models: claude-local`), image settings are absent until a CLI image run overwrites the manifest, and `tasks_completed` lists the finished text tasks

### Step 3: Detect Pipeline Type and Count Outputs

Determine the pipeline type from which files are present:

| Pipeline | Detection Signal | Image Pattern |
|----------|-----------------|---------------|
| **Slide** | `task1-genre.yaml` or `task4-content.yaml` | `slide-NN.{jpg,png}` |
| **Infographic** | `task-i0-analysis.yaml` or `task-i1-design.yaml` | `infographic-vN.{jpg,png}` |

Count images in `$ARGUMENTS/images/` and prompt files in `$ARGUMENTS/prompts/`.

### Step 4: Summarize Key Outputs

Read task YAML files to extract headline information. Be selective — only read what's present:

| Task File | Key Info to Extract |
|-----------|-------------------|
| `task1-genre.yaml` | Genre classification, essay type |
| `task3-structure.yaml` | Number of slides, structure type |
| `task-i0-analysis.yaml` | Content analysis summary |

Don't read entire files — use `yaml.safe_load()` and extract just the top-level keys.

### Step 5: Report

Present a concise status report:

```
Pipeline: infographic
Source: essays/my-essay.md
Style: semi-flat-vector
Provider: gemini

Tasks:
  [OK] i0  task-i0-analysis.yaml
  [OK] i1  task-i1-design.yaml
  [---] i2  task-i2-prompts.yaml

Next step: i2
Images: 0 / 3 variants

Key info:
  - Content type: analytical essay
  - Sections: 5
```

### Step 6: Suggest Next Action

Based on the state, suggest what to do next:

- If no outputs exist: "Run the full pipeline with `/run-pipeline` or start a local task with `/run-local-task`"
- If partially complete: "Resume from `{next_step}` — run `/run-pipeline {pipeline} {source} {dir} --from {next_step}` or `/run-local-task {next_step} {dir}`"
- If all text tasks done but no images: "Text pipeline complete. Run image generation with `/run-pipeline {pipeline} {source} {dir} --from images`"
- If everything done: "Pipeline complete. Review images with `/review-regen {dir}`"
