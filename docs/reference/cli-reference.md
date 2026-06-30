# CLI & Pipeline Reference

`polyptych` turns a source text into visual media. Two pipelines ship:

- **slide** (subcommand `deck`) — a sectioned slide deck from an essay (tasks `task1`…`task7`, then images).
- **infographic** (subcommand `infographic`) — a single-page infographic (tasks `i0`, `i1`, `i2`, then images).

Plus utility subcommands: `validate`, `clean-source`.

## Prerequisites

### Python

```bash
uv sync   # Install all Python dependencies
```

### API keys

Set the API key for whichever provider you use as an environment variable. Gemini is the default for both text and images, so `GOOGLE_API_KEY` alone is enough to run the pipelines end to end.

| Provider | Environment variable |
|----------|---------------------|
| Google Gemini | `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) |
| OpenAI | `OPENAI_API_KEY` |
| xAI | `XAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Vertex AI | Application Default Credentials + `GOOGLE_CLOUD_PROJECT` |

Image generation runs through the `pixbridge` PyPI package and uses the same provider keys (`gemini`, `openai`, `xai`, `vertex`).

## Subcommands

### Common image-generation flags

Both image-producing subcommands (`deck`, `infographic`) accept the same image flags. Per-subcommand lists below call out only the flags that are pipeline-specific.

#### Presets (recommended)

- `--image-preset NAME` — apply a named bundle from `image-presets.yaml` at the repo root (provider/size/aspect-ratio/quality, reusable across both pipelines). Bundled presets: `gem`, `gem-2k`, `gem-lite`, `openai-low`, `openai-medium`, `openai-high`, `xai`. Unknown names get a "did you mean" suggestion.
- `--pipeline-preset NAME` — apply a named bundle from `pipeline-presets.yaml[<pipeline>]` (concurrency + pipeline-specific behavior, scoped per pipeline). Examples: `slide/fast` (concurrent image generation), `infographic/critique` (enable the i2 critique loop). See the YAML for the full list.

**Resolution order** (highest wins): explicit CLI flag > `--pipeline-preset` > `--image-preset` > per-pipeline default > built-in. Non-boolean preset values apply whenever the user did not pass the flag explicitly. Boolean preset values are additive only — they can enable a flag, never disable one the user passed.

#### Individual flags

- `--provider {gemini,openai,xai,vertex}` / `-p` — image generation provider. Per-pipeline default `gemini` when neither preset nor explicit flag sets it.
- `--image-model` — override image model. Resolution: `--image-model` > `$POLYPTYCH_IMAGE_MODEL` (deprecated alias `$SLIDE_GEN_IMAGE_MODEL`) > `image_model_config.yaml` > provider built-in.
- `--size` / `-s` — output image size. For OpenAI gpt-image-2: any `WxH` where both dimensions are divisible by 16, the aspect ratio is within `[1:3, 3:1]`, and `max(W, H) ≤ 3840`. Recommended values: `1024x1024`, `1024x1536`, `1536x1024`, `2048x1152` (true 16:9), `2560x1440`, `3840x2160`. Invalid sizes raise a clear error rather than being silently rewritten. For Gemini: `1K`, `2K`.
- `--aspect-ratio {16:9,4:3,3:4,9:16,1:1}` / `-a` — default `16:9`.
- `--quality {low,medium,high,auto}` / `-q` — OpenAI gpt-image-2 only. When omitted, defaults to `high` for both `deck` and `infographic`.
- `--ref-image PATH` *(repeatable)* — reference image applied to every generated image (brand asset, source chart, exemplar). Requires a provider that supports reference images (`openai` gpt-image-2, `gemini`); other providers raise an error if refs are passed.
- `--output-format {png,jpeg,webp}` — OpenAI gpt-image-2 only; other providers always emit PNG. Default `png`.
- `--compression N` — compression level 0-100 for `--output-format jpeg|webp`. OpenAI gpt-image-2 only.
- `--style PATH` — path to a style-transfer markdown preset. **Sibling-image convention**: if a `<name>.png` / `<name>.jpg` / `<name>.jpeg` / `<name>.webp` exists next to `<name>.md`, it is auto-prepended to the reference list as a visual exemplar (provider-supporting refs only). Presets live in `prompts/style-transfer/`.

#### Common text flags

- `--text-provider {gemini,openai,xai,anthropic,vertex}` — text/LLM provider (default: `gemini`).
- `--text-fallback` — fallback provider chain for content-blocked or transient-error retries (default: auto = all other providers; use `none` to disable).
- `--model` / `-m` — override all LLM models for this run (ignores per-task config). Also settable via `$POLYPTYCH_MODEL` (deprecated alias `$SLIDE_GEN_MODEL`).

### `polyptych deck <source.md>`

Full slide deck pipeline (`task1 → task2 → … → task7 → images`).

- `--output-dir` / `-o` — output directory (default: `./generated/`).
- `--from` — step to start from (`auto`, `task1`…`task7`, `images`; default `auto`, resumes from last valid output). Required upstream outputs must exist.
- `--to` — step to end at (default `images`).
- `--mode` — override genre detection (`auto`, `personal_essay`, `analytical_critique`, `policy_argument`, `fiction`, `strategic_diagnostic`, `conceptual_essay`; default `auto`).
- `--slides` — specific slides to regenerate (e.g. `1,3` or `1-3` or `1-3,5,8-10`). Applies to the image step only.
- `--visuals-only` — generate images without any text elements (pure visuals).
- `--batch-size N` — process Task 7 slides in batches of N (use `1` for one slide at a time, most reliable for large decks).
- `--concurrent N` — run N concurrent image-generation threads (producer-consumer architecture); prompt generation starts immediately.
- `--producers M` — number of concurrent prompt-generation threads (default `min(N, 4)`, requires `--concurrent`).
- `--force` — force regeneration of all items, ignoring existing prompt/image files (requires `--concurrent`).
- `--interleave N` *(deprecated, use `--concurrent`)* — interleave prompt and image generation in chunks of N (implies batch-size 1).
- All common image and text flags above.

### `polyptych infographic <source.md>`

Single-page infographic pipeline (`i0 → i1 → i2 → images`).

- `--output-dir` / `-o` — output directory (default: `./infographic_output/`).
- `--from` — step to start from (`auto`, `i0`, `i1`, `i2`, `images`; default `auto`).
- `--to` — step to end at (default `images`).
- `--variants N` / `-n` — number of infographic prompt variants to generate (1-5, default 3).
- `--style PATH` — style-transfer preset (default: `prompts/style-transfer/infographic/semi-flat-vector.md`).
- `--skip-images` — generate prompts only, skip image generation.
- `--critique` — enable the i2 critique-refine loop (audits prompts against i0/i1 for entity/color consistency, content coverage, flow, and text density before image generation; off by default). Also available as `--pipeline-preset critique`.
- `--critique-rounds N` — number of critique-refine iterations (default 1, requires `--critique`); refinement is skipped early when a round finds no critical/important issues.
- All common image and text flags above.

### `polyptych validate <output_dir> [task_name]`

Validate task YAML outputs against their Pydantic schemas. Detects the pipeline (slide or infographic) from the files present.

- `task_name` — validate a single task (e.g. `task1`, `i2`). If omitted, validates all present outputs.
- `--json` — output results as JSON (includes cross-task findings under `cross_task`).
- **Cross-task checks** (slide pipeline; run automatically when 2+ task files are present, never for a single file): dangling `scene_beat_id` references (task4 → task2), slide-number mismatches across task3/task4/task6/task7, `source_paragraph(s)` beyond the source's paragraph count (when `source.md` is in the output dir), task3 `source_section` values matching no task2 section id/title, arc peaks/nadir pointing at nonexistent slides — all errors (exit 1). Soft content rules (headline > 10 words, quote > 25 words) are warnings and don't affect the exit code.

### `polyptych clean-source <input_file>`

Clean PDF-to-markdown conversion artifacts from a source file.

- `--output` / `-o` — output file path (default: `<stem>-clean.md` in the same directory).
- `--keep-toc` — preserve table of contents.
- `--keep-images` — preserve broken image references.
- `--keep-footnotes` — preserve footnote blocks and superscripts.
- `--keep-page-numbers` — preserve standalone page numbers.
- `--keep-escapes` — preserve backslash escaping.
- `--dry-run` — print the cleaning report without writing output.

## Pipeline Tasks

### Slide pipeline (7 tasks)

| Step | Output file | Purpose |
|------|-------------|---------|
| task1 | `task1-genre.yaml` | Genre classification → parameters |
| task2 | `task2-analysis.yaml` | Source analysis (sections, metaphors, emotional arc) |
| task3 | `task3-structure.yaml` | Slide structure planning (count, arc, roles) |
| task4 | `task4-content.yaml` | Content allocation to slides with paragraph mappings |
| task5 | `task5-design.yaml` | Visual design specification (colors, typography, layouts) |
| task6 | `task6-slides.yaml` | Individual slide specifications |
| task7 | `task7-prompts.yaml` | Image prompt generation per slide |
| images | (pipeline) | Generate images using the selected provider |

**Character canon (fiction).** For fiction sources, task2 additionally emits `character_canon`: one canonical visual description per recurring character (name, age, face, hair, build, costume, distinguishing wear). Task6 uses the exact canonical names in `characters_in_frame`, and task7 embeds each in-frame character's canonical description verbatim into the slide's prompt — injected into the LLM context *and* enforced deterministically in post-processing (a `CHARACTER IDENTITY LOCK` block is appended when the LLM didn't copy the line verbatim). Non-fiction genres are unaffected (`character_canon` is absent). Legacy output dirs whose task2 lacks the field behave as before.

**Provider tuning.** Task7 injects `prompts/providers/<provider>-best-practices.md` into its LLM context, so the generated prompts are tuned for the image provider selected *at task7 time* (`--provider` / `--image-preset`; default gemini). The provider the prompts were authored for is recorded as `prompt_provider` in `task7-prompts.yaml`. When images are later generated with a different provider (e.g. resuming with `--from images` and a different preset), the pipeline prints a warning naming both providers — re-run task7 (`--from task7 --provider <actual>`) to retune the prompts. Output dirs predating this field produce no warning.

### Infographic pipeline (3 tasks + optional critique loop)

| Step | Output file | Purpose |
|------|-------------|---------|
| i0 | `task-i0-analysis.yaml` | Content analysis for infographic layout |
| i1 | `task-i1-design.yaml` | Infographic design specification |
| i2 | `task-i2-prompts.yaml` | Image prompts (N variants) |
| i2_critique / i2_refine | `task-i2-N-critique.yaml` | Critique-refine loop for i2 prompts (opt-in via `--critique`) |
| images | (pipeline) | Generate infographic images |

## Genres

Task 1 classifies content into one of six genres, each with different downstream parameters:

- **personal_essay** — first-person narratives with emotional reflection
- **analytical_critique** — third-person analytical arguments
- **policy_argument** — systems-focused arguments with human stakes
- **fiction** — narrative fiction with characters and dialogue
- **strategic_diagnostic** — strategic/diagnostic analysis
- **conceptual_essay** — definition- and distinction-driven philosophical arguments

Use `--mode <genre>` to override auto-detection.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `GOOGLE_API_KEY` or `GEMINI_API_KEY` | Gemini API access (text + images) |
| `OPENAI_API_KEY` | OpenAI text generation and `gpt-image-2` image generation |
| `XAI_API_KEY` | xAI Grok text generation and image generation |
| `ANTHROPIC_API_KEY` | Anthropic text generation (Claude models, supports `thinking_budget`) |
| `GOOGLE_CLOUD_PROJECT` | Required project ID for the Vertex AI provider; auth via ADC |
| `POLYPTYCH_MODEL` | Override all LLM models (ignores per-task config). `--model` takes precedence. |
| `POLYPTYCH_IMAGE_MODEL` | Override image generation model for all providers. `--image-model` takes precedence. |
| `POLYPTYCH_LOG_LEVEL` | Default log level (`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`). `--log-level` takes precedence. |
| `POLYPTYCH_USAGE_LOG` | Path for the API usage JSONL log. Default: `~/.cache/polyptych/usage.jsonl`. Pipelines that write to their own output dir (e.g. `output_dir/usage.jsonl`) are unaffected — this controls only the fallback used when no explicit path is passed. |

> **Deprecated aliases.** The `POLYPTYCH_*` env vars above were renamed from `SLIDE_GEN_*`. The old `SLIDE_GEN_MODEL`, `SLIDE_GEN_IMAGE_MODEL`, `SLIDE_GEN_LOG_LEVEL`, and `SLIDE_GEN_USAGE_LOG` names still work as a fallback (a one-time deprecation warning is logged on first use) but will be removed in a future release. When both are set, the `POLYPTYCH_*` name wins.

### Runtime directories

| Path | Purpose |
|------|---------|
| `~/.cache/polyptych/usage.jsonl` | Default API usage log (LLM + image). Override with `POLYPTYCH_USAGE_LOG`. |
| `~/.cache/polyptych/blocked-requests.jsonl` | Blocked-request debug log (written alongside `usage.jsonl` when content is rejected). |

## Generated Output Structure

### Slide pipeline (`generated/`)
```
generated/<num>/
  source.md              # Copy of source essay
  task1-genre.yaml       # Genre classification
  task2-analysis.yaml    # Source analysis
  task3-structure.yaml   # Structure planning
  task4-content.yaml     # Content allocation
  task5-design.yaml      # Visual design spec
  task6-slides.yaml      # Slide specifications
  task7-prompts.yaml     # Image prompts
  prompts/               # Per-slide prompt YAMLs (slide-NN-prompt.yaml)
  images/                # Generated slide images
  manifest.yaml          # Resolved run configuration
```

### Infographic pipeline (`infographic_output/`)
```
infographic_output/
  source.md
  task-i0-analysis.yaml      # Content analysis
  task-i1-design.yaml        # Design specification
  task-i2-prompts.yaml       # Image prompt variants (final, post-refine when --critique)
  task-i2-N-prompts.yaml, task-i2-N-critique.yaml  # (critique rounds, --critique only)
  prompts/                   # infographic-NNN-prompt.yaml
  images/                    # Generated infographic images (infographic-vN.{ext})
  manifest.yaml
```

Every run writes `manifest.yaml` capturing the resolved configuration (`image_provider`, `image_quality`, `image_size`, `aspect_ratio`, `style_prompt`, models, git commit). Read it before opening images — the resolved settings (after argparse defaults and preset expansion) usually explain why an image looks the way it does.

## just Targets

Pipeline runs go through one unified target plus per-pipeline passthroughs. Flag combinations are named in `image-presets.yaml` and `pipeline-presets.yaml` instead of in target names.

**Dev targets:** `install`, `test`, `coverage`, `typecheck`, `fmt`, `lint`, `validate DIR`, `clean-source FILE`, `clean DIR`, `help`.

**Generation:**

- `gen PIPELINE +ARGS` — universal entry point. Example: `just gen infographic sources/x.md --output-dir generated/x --style prompts/style-transfer/infographic/semi-flat-vector.md --image-preset openai-low`.
