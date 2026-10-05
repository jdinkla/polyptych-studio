---
id: TASK-7
title: Re-calibrate in-image text density per image model and quality tier
status: To Do
assignee: []
created_date: '2026-10-05 16:19'
labels:
  - prompts
  - experiment
dependencies: []
priority: low
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
prompts/tasks/task-i2-prompts.md ('Calibrating Text Density to the Quality Tier') limits low-tier prompts to a title, section headers, and a handful of labels. That rule was written for gpt-image-2. In a 2026-10 run, gpt-image-2.5-sunburst at quality low rendered about 25 short German strings (umlauts, ≈, €) without errors. One sample is not enough to loosen the rule; measure first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Run the same i2 prompt at 3 text densities (about 10, 25, 40 strings) on gpt-image-2.5-sunburst and gpt-image-2.5-flare at low and medium, and on the default Gemini image model
- [ ] #2 Record per image: strings requested, strings rendered exactly, garbled strings, cost from usage.jsonl
- [ ] #3 Update the calibration section with per-model guidance only where the data supports it, and note the sample size
- [ ] #4 Results are saved under docs/explanation/ or the task notes
<!-- AC:END -->
