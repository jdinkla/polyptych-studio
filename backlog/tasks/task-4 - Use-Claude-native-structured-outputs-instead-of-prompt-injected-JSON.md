---
id: TASK-4
title: Use Claude native structured outputs instead of prompt-injected JSON
status: To Do
assignee: []
created_date: '2026-10-05 16:19'
labels:
  - providers
dependencies:
  - TASK-1
priority: medium
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
AnthropicTextProvider.generate_structured (src/polyptych/providers/anthropic.py) appends the JSON schema to the prompt inside a ```json fence and parses the reply text. Claude Sonnet 5.5 copies the fence back; strip_code_fence in providers/base.py now absorbs that, but parsing free text remains fragile. OpenAI and xAI already use json_schema response formats. Switch Claude to the Messages API's native structured outputs for the current Claude models, keeping the prompt-injection path for models that do not support it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Claude models that support structured outputs (check platform.claude.com docs for the current list) are called with the native schema parameter and no schema text in the prompt
- [ ] #2 Unsupported (legacy) models keep the existing prompt-injected path
- [ ] #3 Request-shape unit tests cover both paths
- [ ] #4 The live integration suite (TASK-1) passes for the anthropic fast and thinking tiers
- [ ] #5 'just test' and 'just lint' pass
<!-- AC:END -->
