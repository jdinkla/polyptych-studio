---
name: edit-output
description: Modify a pipeline task YAML output, validate it, and identify downstream tasks that need re-running
argument-hint: <output-dir> <task-name> <change-description>
---

# Edit Pipeline Output — Modify and Resume

## Role

You modify intermediate pipeline task outputs (YAML files), validate the changes against the Pydantic schema, and identify which downstream tasks need to be re-run.

## Arguments

Parse from `$ARGUMENTS`:
- **output-dir**: Path to the output directory
- **task-name**: Which task output to edit (e.g., `task1`, `i0`, `i2`)
- **change-description**: Natural language description of what to change (e.g., "change slide 3's headline to...", "tighten the i1 color palette", "drop section 4 from the infographic")

If arguments are missing, ask the user.

## Task Output Files

| Task | Output File | Model Class |
|------|-------------|-------------|
| task1 | `task1-genre.yaml` | `Task1Output` |
| task2 | `task2-analysis.yaml` | `Task2Output` |
| task3 | `task3-structure.yaml` | `Task3Output` |
| task4 | `task4-content.yaml` | `Task4Output` |
| task5 | `task5-design.yaml` | `Task5Output` |
| task6 | `task6-slides.yaml` | `Task6Output` |
| task7 | `task7-prompts.yaml` | `Task7Output` |
| i0 | `task-i0-analysis.yaml` | `TaskI0Output` |
| i1 | `task-i1-design.yaml` | `TaskI1Output` |
| i2 | `task-i2-prompts.yaml` | `TaskI2Output` |

## Dependency Graph

Tasks that depend on the edited task will need re-running. Here are the downstream dependencies:

### Slide Pipeline
```
task1 → task2, task3, task4, task5, task6, task7
task2 → task3, task4, task5, task6
task3 → task4, task6
task4 → task5, task6
task5 → task6, task7
task6 → task7
task7 → images
```

### Infographic Pipeline
```
i0 → i1, i2, images
i1 → i2, images
i2 → images
```

## Process

### Step 1: Read Current Output

Read the task YAML file from `$OUTPUT_DIR/<output-file>`.

If the file doesn't exist, report it and stop.

### Step 2: Read the Pydantic Model

Read the model class definition from `src/polyptych/models.py` to understand the schema constraints:
- Required fields and types
- Nested model structures
- Value constraints (min/max, enums, list lengths)

### Step 3: Apply Changes

Based on the change description, modify the YAML data. Common edit patterns:

- **Change a field value**: Update the specific field
- **Add an item to a list**: Append with all required fields filled
- **Remove an item**: Delete from the list (may need to renumber)
- **Modify nested data**: Navigate to the correct nesting level
- **Bulk changes**: Apply the same change across multiple items

Preserve all fields that aren't being changed. Don't reformat or restructure unchanged data.

### Step 4: Validate

Run schema validation:

```bash
uv run polyptych validate $OUTPUT_DIR $TASK_NAME
```

If validation fails:
- Read the error message
- Fix the issue (missing required field, wrong type, constraint violation)
- Re-validate

After saving, also run directory-level validation (`uv run polyptych validate $OUTPUT_DIR --json`): with 2+ task files present it performs cross-task checks (dangling scene_beat_ids, slide-set mismatches, out-of-range paragraph references, ...), which catch edits that broke references *between* files — e.g. removing a scene beat that a task4 allocation still cites.

### Step 5: Save

Write the modified YAML back to the output file, overwriting the original.

### Step 6: Identify Downstream Impact

Using the dependency graph above, list all downstream tasks that may need re-running because they depend on the edited task.

Categorize them:
- **Direct dependents**: Tasks that directly read this task's output
- **Transitive dependents**: Tasks that depend on direct dependents

### Step 7: Suggest Resume Command

Build the command to re-run downstream tasks. The earliest downstream step is where to resume:

```
To re-run affected downstream tasks:
  just <target> SOURCE OUTPUT STYLE --from <earliest-affected-step>

Or selectively re-run specific tasks:
  /run-local-task <task-name> <output-dir>
  /run-pipeline <pipeline> <source> <output-dir> --from <step> --to <step>
```

If only the images step is affected (e.g., editing image prompts in task7/i2), suggest:
```
  /run-pipeline <pipeline> <source> <output-dir> --from images
```

## Notes

- Always back up the original file mentally — if the edit goes wrong, the user can recover from git
- For large edits (e.g., restructuring all slides), consider whether `/run-local-task` to regenerate the entire task would be faster than manual editing
- When editing list items (slides, scenes, beats), be careful about maintaining consistent numbering and cross-references
- If the change affects counts (e.g., adding slides), downstream tasks that reference the count may produce inconsistent output — flag this
