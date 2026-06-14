# Changelog

All notable changes to Polyptych Studio are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-14

### Added

- **`polyptych.ext` extension API** — a stable, documented public surface for
  building additional pipelines on top of the core without forking: registry
  builders (`build_output_files`/`build_models`/`build_step_deps`), the core
  task-spec list (`CORE_TASK_SPECS`) and `task_spec`/`TaskSpec` primitives, the
  `PipelineRunConfig` base and option mixins, the preset lookup tables, prompt
  loaders, the slide/infographic pipeline mixins, and the CLI arg-adders,
  command handlers, and `build_parser`. Re-exports existing internals under
  stable names; no behavior change.

## [0.1.0] - 2026-06-14

First open-source release.

### Added

- **Slide pipeline** (`polyptych deck`) — essay → sectioned slide deck via text
  tasks `task1`→`task7` plus image generation.
- **Infographic pipeline** (`polyptych infographic`) — essay → single-page
  infographic(s) via text tasks `i0`→`i2` plus image generation, N variants.
- Multi-provider text generation with a fallback chain (Gemini, OpenAI, xAI,
  Anthropic, Vertex AI) and multi-provider image generation via
  [`pixbridge`](https://pypi.org/project/pixbridge/).
- `polyptych validate` and `polyptych clean-source` subcommands.
- Reusable configuration: `model_config.yaml`, `image_model_config.yaml`,
  `image-presets.yaml`, `pipeline-presets.yaml`, and style-transfer presets.
- Agent skills under `.claude/` for autonomous pipeline operation.
