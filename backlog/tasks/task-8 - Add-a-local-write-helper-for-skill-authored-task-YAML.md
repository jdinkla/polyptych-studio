---
id: TASK-8
title: Add a local-write helper for skill-authored task YAML
status: To Do
assignee: []
created_date: '2026-10-05 16:20'
labels:
  - delegate
  - skills
dependencies: []
priority: medium
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Local skill runs (/infographic, /run-local-pipeline, /run-local-task) have the agent write task YAML by hand, then run several manual steps that are easy to miss: validate the schema, record provenance via polyptych.ext.record_task_provenance, and update manifest.yaml. In a 2026-10 run a hand-written YAML list item containing ': ' parsed as a mapping and failed validation. Provide one CLI command that does all of this from a JSON or YAML input.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 'polyptych local-write OUTPUT_DIR TASK INPUT_FILE --model MODEL_ID' accepts JSON or YAML, validates against the task's Pydantic model (same registry as 'polyptych validate'), and writes the canonical task YAML
- [ ] #2 For i2 and task7 it folds negative_prompts into full_prompt using the existing fold helpers (idempotent)
- [ ] #3 It merge-updates provenance.yaml with mode local and the given model, and creates or updates manifest.yaml (pipeline, mode: local, timestamp, git_commit, source if given, tasks_completed) using the field names from the run-local-pipeline skill
- [ ] #4 Invalid input exits non-zero with the validation error and writes nothing
- [ ] #5 The infographic, run-local-pipeline and run-local-task skills use the command instead of manual write/validate/provenance steps
- [ ] #6 Unit tests cover valid input, invalid input, negative folding, and manifest merge; 'just test' and 'just lint' pass
<!-- AC:END -->
