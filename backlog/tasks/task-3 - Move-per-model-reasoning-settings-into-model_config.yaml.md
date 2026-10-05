---
id: TASK-3
title: Move per-model reasoning settings into model_config.yaml
status: To Do
assignee: []
created_date: '2026-10-05 16:19'
labels:
  - providers
  - design
dependencies:
  - TASK-2
priority: medium
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Per-model reasoning tables live in code across four provider files (openai.py, xai.py, anthropic.py, gemini.py), keyed by model-id prefix. Adopting a new model needs a code change plus a config change, and the 2026-10 Claude 5.5 upgrade showed prefix matching is fragile (claude-sonnet-5-5 matched the claude-sonnet-5- entry). Decide whether the mapping (fast-tier setting, thinking-tier setting, rejected fields) belongs in model_config.yaml and design the schema. Depends on the warning task so unmapped ids are visible during the migration.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A short design note (ADR via /software-craft:adr-create or a section in docs/explanation/) chooses config vs code and justifies it
- [ ] #2 If config: model_config.yaml gains a per-model reasoning section; all four providers read it; the code tables are removed; existing request-shape tests in tests/polyptych/providers/test_model_requests.py pass unchanged
- [ ] #3 If code: the tables move into one module with exact-id plus explicit snapshot-suffix matching, and the ADR records why
- [ ] #4 check-models skill step 4 is updated to point at the new location
<!-- AC:END -->
