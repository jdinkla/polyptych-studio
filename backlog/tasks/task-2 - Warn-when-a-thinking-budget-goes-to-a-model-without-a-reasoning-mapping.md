---
id: TASK-2
title: Warn when a thinking budget goes to a model without a reasoning mapping
status: To Do
assignee: []
created_date: '2026-10-05 16:19'
labels:
  - delegate
  - providers
dependencies: []
priority: high
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Providers translate thinking_budget into reasoning settings only for model ids listed in per-provider tables: _reasoning_kwargs in src/polyptych/providers/openai.py and xai.py, _ADAPTIVE_THINKING_OFF in anthropic.py, _thinking_config in gemini.py. Any other model id silently gets provider defaults, so a new model added to model_config.yaml can run every task at the wrong effort, or be sent request fields it rejects, with no signal. Add a one-time warning when a positive thinking_budget reaches a model with no mapping.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each of the four providers logs one warning per (provider, model) per process via the logging module when thinking_budget is truthy and the model matches no mapping entry; the message names the model and says provider defaults are used
- [ ] #2 No warning for mapped models (e.g. gpt-6-astra, grok-4.7, claude-opus-5-5, gemini-3.8-flash) or when thinking_budget is None/0
- [ ] #3 Legacy Claude models that use manual budget_tokens (no adaptive mapping) still get budget_tokens and no warning
- [ ] #4 Unit tests with mocked SDK clients cover: warning emitted once, no warning for mapped ids, no warning without budget
- [ ] #5 'just test' and 'just lint' pass
<!-- AC:END -->
