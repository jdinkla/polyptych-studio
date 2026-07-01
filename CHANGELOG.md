# Changelog

All notable changes to Polyptych Studio are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **`generation_notes.negative_prompts` now reaches the image providers.** No
  pixbridge provider reads the `negative_prompts` field — providers send only
  `full_prompt` — so the negatives both pipelines carefully author (style
  forbidden-elements, "no text" rules, brand-logo bans) were inert metadata.
  They are now folded into the prompt text as a single trailing `AVOID: ...`
  line at every seam that finalizes a prompt: slide task7's deterministic
  assembly (`finalize_draft`), infographic i2 generation, and the i2
  critique-refine pass (which replaces variants wholesale). The fold is
  idempotent and skips empty/blank entries; prompts without negatives are
  unchanged.

## [0.3.0] - 2026-06-30

### Added

- **`gem-lite` image preset** — an opt-in bundle targeting Google's Nano Banana 2
  Lite (`gemini-3.1-flash-lite-image`), the cheapest/fastest member of the Nano
  Banana 2 family. Resolves to `provider: gemini`, `size: 1K`, `aspect-ratio:
  16:9` with the Lite model id carried as an `image-model` override, so it works
  without touching `image_model_config.yaml` or the provider defaults. Pinned to
  1K because Lite is 1K-only. Use it via `--image-preset gem-lite` when cheap,
  high-volume image generation is needed; all defaults are unchanged.

## [0.2.1] - 2026-06-20

### Fixed

- **Image-generation failures no longer print a stack trace.** A failed
  per-image request (e.g. an OpenAI output-moderation block) already logs a
  one-line warning carrying the error; the redundant `exc_info=True` traceback
  on the `polyptych.image_batch` logger has been dropped and the error message
  folded into that warning, so the log stays a clean one-liner.
- **Resuming a run no longer crashes when `source_file` is the output dir's own
  `source.md`.** `PipelineBase.__init__` copied the source into the output
  directory unconditionally, so a resume command that passed
  `<output_dir>/source.md` (the path the first run wrote) raised
  `shutil.SameFileError` before any work ran. The copy is now skipped when the
  source and destination resolve to the same file.

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

### Fixed

- **Packaged data is now bundled into the wheel.** The config YAMLs
  (`model_config.yaml`, `image_model_config.yaml`, `image-presets.yaml`,
  `pipeline-presets.yaml`) and the `prompts/` tree are force-included under
  `polyptych/_data/`, and the loaders resolve them via
  `polyptych._datafiles.data_root` (bundled dir for wheel installs, repo root
  for editable/source checkouts). A plain `pip install polyptych` previously
  failed at runtime with `model_config.yaml not found` / `Prompts directory not
  found` because the wheel shipped only `.py` modules.

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
