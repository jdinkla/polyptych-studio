---
id: TASK-5
title: >-
  Record actual image dimensions and align preset size with requested aspect
  ratio
status: To Do
assignee: []
created_date: '2026-10-05 16:19'
labels:
  - images
  - design
dependencies: []
priority: medium
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In a 2026-10 infographic run, i1 chose landscape (the i2 template maps landscape to 16:9), the prompt said 16:9, the openai-low preset sent size 1536x1024 (3:2), and manifest.yaml recorded aspect_ratio '4:3'. pixbridge's OpenAI provider lets aspect_ratio override size, so which one wins depends on the call path. The image was fine, but the manifest misdescribes it and the prompt's aspect claim can contradict the canvas. Decide one rule for size vs aspect ratio, and record what was actually produced.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 manifest.yaml (or the per-image usage record) stores the actual pixel width and height of each generated image, read from the file
- [ ] #2 A documented rule (docs/reference/cli-reference.md) states which of --size, preset size, and i1/i2 aspect ratio wins for each provider
- [ ] #3 For openai-* presets, the canvas aspect ratio matches the aspect ratio stated in the i2 prompt (either the preset adopts a 16:9 size such as 2048x1152, or i2 takes its ratio from the preset)
- [ ] #4 Tests cover the chosen precedence; 'just test' passes
<!-- AC:END -->
