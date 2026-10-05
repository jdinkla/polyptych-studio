---
id: TASK-1
title: Add a live integration smoke suite for configured models
status: To Do
assignee: []
created_date: '2026-10-05 16:19'
labels:
  - delegate
  - testing
dependencies: []
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The pytest marker 'integration' is declared in pyproject.toml, but no test uses it, so 'just test-integration' collects nothing. Unit tests mock the provider SDKs and cannot catch request shapes a model rejects. In 2026-10 a mocked suite passed while Claude Sonnet 5.5 rejected thinking:{type:disabled} with a 400 and returned code-fenced JSON that failed to parse; both were only found by a throwaway live script. Build a small, cheap live suite under tests/integration/ that exercises each provider configured in model_config.yaml through polyptych's own provider classes (src/polyptych/providers/*), plus one image.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tests/integration/ exists; every test there carries @pytest.mark.integration and is excluded from 'just test'
- [ ] #2 For each provider in model_config.yaml providers (gemini, openai, xai, anthropic, vertex): one generate_structured call for the fast tier (thinking_budget=None) and one for the thinking tier (thinking_budget=resolve_thinking_budget(...)), using a one-field Pydantic schema and a prompt like 'What is 2+2?'
- [ ] #3 Each provider's tests skip (not fail) when its credentials are absent (provider ENV_KEYS; vertex needs GOOGLE_CLOUD_PROJECT)
- [ ] #4 One image test generates a single image via ImageClient with the openai provider, the model from resolve_image_model(load_image_model_config(), 'openai'), quality 'low', into tmp_path
- [ ] #5 Debug dumps and images land in tmp_path, never in the repo (set POLYPTYCH_DEBUG_DIR to tmp_path)
- [ ] #6 'just test-integration' collects at least 11 tests; 'just test' passes and still deselects them; 'just lint' is clean
<!-- AC:END -->
