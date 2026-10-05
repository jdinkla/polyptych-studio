---
id: TASK-9
title: Fix pre-existing prompt and doc drift from the 2026-10 consistency review
status: To Do
assignee: []
created_date: '2026-10-05 16:25'
labels:
  - delegate
  - docs
dependencies: []
priority: low
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A prompt-consistency review on 2026-10-05 found drift that predates the GPT Image 2.5 / Claude 5.5 changes. Each item names the file and the fix; all are doc or prompt edits checkable by grep plus the test suite. The new language rule for in-image text already exists in the infographic templates (task-i0/i1/i2, critique, refine); the slide templates still lack it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 prompts/providers/gemini-best-practices.md names gemini-3-pro-image (or 'see image_model_config.yaml') as the default model, not gemini-3.1-flash-image, and its text-rendering claim is model-neutral
- [ ] #2 gemini-best-practices.md lists only the sizes (1K, 2K) and aspect ratios (16:9, 4:3, 3:4, 9:16, 1:1) the CLI exposes, or marks the rest as API-only
- [ ] #3 Slide templates task-06-slide-specification.md, task-06-slide-specification-fiction.md and task-07-image-generation.md state that in-image text uses the source language and quoted strings are never translated (same wording as prompts/tasks/task-i2-prompts.md 'Language of In-Image Text')
- [ ] #4 The preset lists in CLAUDE.md ('Available: ...'), docs/reference/cli-reference.md ('Bundled presets: ...') and .claude/skills/run-pipeline/SKILL.md include gem-lite and mention the flare-* / sunburst-* presets
- [ ] #5 docs/reference/cli-reference.md names the per-variant prompt file infographic-v{N}-prompt.yaml, matching src/polyptych/pipeline_infographic.py
- [ ] #6 prompts/tasks/task-critique.md and the model_config.yaml 'enrichment' tier are either removed or labeled as unused, after confirming with grep that nothing loads them (tests/polyptych/test_task_registry.py excludes enrichment on purpose: keep that test passing)
- [ ] #7 'just test' and 'just lint' pass
<!-- AC:END -->
