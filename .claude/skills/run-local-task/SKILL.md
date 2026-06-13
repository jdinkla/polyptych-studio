---
name: run-local-task
description: Execute a pipeline task locally (Claude generates the YAML output instead of calling an external LLM)
argument-hint: <task-name> <output-dir> [--source <source-file>]
---

# Local Task Execution — Claude as the LLM

## Role

You execute a pipeline task yourself — reading the prompt template, source essay, and dependency outputs, then generating structured YAML that conforms to the task's Pydantic schema. This avoids external API calls for tasks you can handle directly.

## Arguments

Parse from `$ARGUMENTS`:
- **task-name**: The task to execute (e.g., `task1`, `task3`, `i0`, `i1`, `i2`)
- **output-dir**: Path to the output directory
- **--source** (optional): Path to the source essay. If omitted, look for `source.md` in the output dir, or read `manifest.yaml` to find the source path.

If required arguments are missing, ask for them.

## Task Registry

This maps each task to its prompt template, Pydantic model class, output filename, and dependencies.

### Slide Pipeline

| Task | Prompt File | Model Class | Output File | Dependencies |
|------|-------------|-------------|-------------|--------------|
| task1 | `prompts/tasks/task-01-genre-classification.md` | `Task1Output` | `task1-genre.yaml` | — |
| task2 | `prompts/tasks/task-02-source-analysis.md` | `Task2Output` | `task2-analysis.yaml` | task1 |
| task3 | `prompts/tasks/task-03-structure-planning.md` | `Task3Output` | `task3-structure.yaml` | task1, task2 |
| task4 | `prompts/tasks/task-04-content-allocation.md` | `Task4Output` | `task4-content.yaml` | task1, task2, task3 |
| task5 | `prompts/tasks/task-05-visual-design.md` | `Task5Output` | `task5-design.yaml` | task1, task2, task4 |
| task6 | `prompts/tasks/task-06-slide-specification.md` | `Task6Output` | `task6-slides.yaml` | task1, task2, task3, task4, task5 |
| task7 | `prompts/tasks/task-07-image-generation.md` | `Task7Output` | `task7-prompts.yaml` | task1, task5, task6 |

### Infographic Pipeline

| Task | Prompt File | Model Class | Output File | Dependencies |
|------|-------------|-------------|-------------|--------------|
| i0 | `prompts/tasks/task-i0-analysis.md` | `TaskI0Output` | `task-i0-analysis.yaml` | — |
| i1 | `prompts/tasks/task-i1-design.md` | `TaskI1Output` | `task-i1-design.yaml` | i0 |
| i2 | `prompts/tasks/task-i2-prompts.md` | `TaskI2Output` | `task-i2-prompts.yaml` | i0, i1 |

## Process

### Step 1: Locate the Source Essay

Find the source essay in this order:
1. `--source` argument if provided
2. `$OUTPUT_DIR/source.md` — many pipelines copy the source here
3. `$OUTPUT_DIR/manifest.yaml` → read the `source` field for the original filename
4. Ask the user

### Step 2: Read the Prompt Template

Read the prompt template from `prompts/tasks/<prompt-file>.md` per the task registry above.

This is the **system prompt** that the external LLM would receive. It describes the task objectives, constraints, and expected output format.

### Step 3: Read the Task Implementation

Read the corresponding task Python file from `src/polyptych/tasks/task_*.py` to understand:
- How the **user prompt** is constructed (what context is injected)
- What additional formatting or instructions are added beyond the prompt template
- Any special handling (e.g., genre-specific prompt variants for task6)

This tells you exactly what information the LLM receives. Replicate that context.

### Step 4: Read Dependencies

For each dependency listed in the task registry, read the corresponding YAML file from the output directory. These are injected into the user prompt by the task implementation.

If a dependency is missing, report it and stop — the task can't run without its inputs.

### Step 5: Read the Pydantic Model

Read the model class definition from `src/polyptych/models.py` to understand the exact schema:
- Required fields and their types
- Nested model structures
- Field descriptions and constraints (min/max values, string patterns)
- Optional fields

### Step 6: Generate the Output

With all context assembled (system prompt + source essay + dependency outputs + schema), generate the task output as structured YAML.

**Critical rules:**
- The output MUST be valid YAML
- The output MUST conform to the Pydantic model schema exactly
- Use the same field names as defined in the model
- Respect all constraints (list lengths, value ranges, enum values)
- Match the quality expectations described in the prompt template
- For list fields, generate the expected number of items (e.g., if the task says "one per slide", match the slide count)

Write the YAML output to a temporary string first, then validate before saving.

### Step 7: Validate

Run schema validation on the generated output:

```bash
uv run polyptych validate $OUTPUT_DIR $TASK_NAME
```

If validation fails, read the error message, fix the YAML, and try again.

### Step 8: Save

Write the validated YAML to `$OUTPUT_DIR/<output-file>` as specified in the task registry.

Create the output directory if it doesn't exist:
```bash
mkdir -p $OUTPUT_DIR
```

### Step 9: Report

After saving, report:
- Task name and output file path
- Brief summary of what was generated (e.g., "Generated genre classification: analytical_critique")
- Validation status
- What to run next (the next task in the pipeline sequence)

## Quality Guidance

**Tasks that work well locally** (structured, schema-driven, shorter reasoning chains):
- `task1` — Genre classification (short, categorical)
- `task3` — Structure planning (builds on task1+task2)
- `task5` — Visual design specification
- `task7` — Image prompt generation
- `i0` — Content analysis
- `i1` — Design specification
- `i2` — Image prompt generation
- All critique tasks

**Tasks that are harder locally** (require deep analysis, long-form reasoning):
- `task2` — Source analysis (deep reading comprehension)
- `task4` — Content allocation (complex mapping)
- `task6` — Slide specification (detailed per-slide content)

For harder tasks, consider whether external LLM execution via `/run-pipeline` might produce better results. It's always the agent's choice.

## Notes

- Always create the output directory before writing: `mkdir -p $OUTPUT_DIR`
- The YAML must use the exact field names from the Pydantic model, not the prompt template's natural language descriptions
- If the prompt template references "sections" but the model uses "slides", use "slides"
- For tasks with critique/refine cycles, you can run the base task locally and optionally self-critique before saving
- For image-prompt tasks (task7, i2): read `prompts/providers/<provider>-best-practices.md` for the intended image provider and apply it while writing the prompts. For `task7`, also set the top-level `prompt_provider: <provider>` field in `task7-prompts.yaml` — the CLI warns at image time when the actual provider differs from the recorded one
- `task7` writes each prompt once: author the `sections`, then set `full_prompt` to the deterministic assembly of those sections (order: GOAL, SUBJECT, COMPOSITION, SPATIAL RELATIONSHIPS (if any), SETTING, LIGHTING, TEXT ELEMENTS (if any), STYLE, FIDELITY, CONSISTENCY; `"SECTION: text"` paragraphs joined by blank lines — mirrors `assemble_full_prompt()` in `src/polyptych/tasks/task_07_prompts.py`). `text_elements` must include the slide's callout with the design system's `callout_treatment` `visual_spec` when `content.callout` is set
- Fiction slide pipeline: `task2` emits `character_canon` (canonical per-character visual descriptions); `task6` must use those exact names in `characters_in_frame`; `task7` must embed each in-frame character's canonical description verbatim on every slide (see the run-local-pipeline skill, "Fiction Character Canon")
- Maintain `manifest.yaml` in the output dir: if none exists, create one with `pipeline`, `mode: local`, `timestamp` (UTC ISO-8601), `git_commit` (short hash), `source` (basename), `models: claude-local`, plus `style_prompt` when applicable and `tasks_completed: [<this task>]` (field template in the run-local-pipeline skill, Step 4). If one exists, add the task to `tasks_completed` and refresh `timestamp`/`git_commit`. CLI runs overwrite it with the full CLI manifest later — expected.
