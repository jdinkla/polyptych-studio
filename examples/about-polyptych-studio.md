# Polyptych Studio: Turning Essays into Visual Media

Polyptych Studio is an open-source, essay-to-visuals generation system. Feed it
a single markdown source text and it produces finished visual media — either a
multi-slide presentation deck or a single-page infographic — by decomposing the
work into a chain of specialized LLM tasks and then generating images from the
structured plan those tasks produce.

The name comes from the *polyptych*: a painting split across many hinged panels
that together tell one story. That is exactly what the system does — it breaks
one essay into many coordinated visual panels.

## Two independent pipelines

The studio ships two fully independent pipelines. Each takes the same kind of
input (a markdown essay) and runs unattended end-to-end: all text tasks run
first, then image generation.

### Slide pipeline — 7 tasks

The slide pipeline converts an essay into a presentation deck of roughly 10–30
slides, each with a generated image. It runs a 7-stage chain:

1. **Genre classification** — fiction vs. non-fiction, which steers later stages
2. **Source analysis** — extract themes, structure, and key content
3. **Structure planning** — decide the slide sequence and narrative arc
4. **Content allocation** — assign source material to individual slides
5. **Visual design** — define the visual language for the deck
6. **Slide specification** — write each slide (a dedicated fiction variant exists)
7. **Image generation** — turn each slide spec into a final image prompt

### Infographic pipeline — 3 tasks

The infographic pipeline distills an essay into one dense visual page. It runs a
3-stage chain built around a **critique/refine loop**:

- **i0 — analysis**: extract the key points, data, and relationships worth showing
- **i1 — design**: lay out the single-page composition
- **i2 — critique → refine → prompts**: a reviewer agent critiques the design,
  the design is refined in response, and final image prompts are produced

## Multi-provider by design

Nothing in the studio is locked to one vendor. Text generation runs through a
**5-provider fallback chain**, and image generation spans **4 providers** via
the companion `pixbridge` PyPI package.

| Capability | Providers |
|------------|-----------|
| Text generation | Gemini, OpenAI, xAI, Anthropic, Vertex AI |
| Image generation | Gemini, OpenAI, xAI, Vertex AI |

Per-task model tiers (fast vs. thinking) are configured in `model_config.yaml`,
so cheap tasks use cheap models and reasoning-heavy tasks use stronger ones.

## Two ways to drive it

- **Python CLI** — one entry point, `polyptych`, with subcommands `deck`,
  `infographic`, `validate`, and `clean-source`. Best for scripts, CI, and
  reproducible batch runs.
- **Claude Code skills** — 16 slash commands (e.g. `/run-pipeline`,
  `/infographic`, `/review-regen`) let Claude operate the pipelines
  interactively, running text tasks locally at **zero API cost**.

## Reusable style and configuration

Visual style is decoupled from content. **6 example style-transfer presets**
ship across 5 families — anime, editorial, infographic, noir, and period-art —
and any preset can be applied to either pipeline with a single `--style` flag.
Image behavior is bundled into named presets (`image-presets.yaml`) and pipeline
behavior into another set (`pipeline-presets.yaml`).

## By the numbers

A snapshot of the codebase, measured with `scc`:

| Metric | Value |
|--------|-------|
| Total files | 156 |
| Total lines of code | 23,414 |
| Python (code lines) | 14,391 across 91 files |
| Markdown docs (code lines) | 8,653 across 55 files |
| Cyclomatic complexity (Python) | 892 |
| Automated tests passing | 513 |
| Text providers | 5 |
| Image providers | 4 |
| Slide pipeline tasks | 7 |
| Infographic pipeline tasks | 3 |
| Style-transfer presets | 6 |
| Claude Code skills | 16 |
| License | Apache-2.0 |
| Estimated cost to develop (organic) | ~$740,000 |

## Quality and engineering

Every change is gated by a 3-check CI pipeline: linting (`ruff`), strict type
checking (`pyright`, zero errors required), and the unit-test suite (513 tests,
integration tests that call paid APIs are excluded). Documentation follows the
Diátaxis framework — split into tutorials, how-to guides, reference, and
explanation — so newcomers and maintainers each have a clear entry point.

## The core idea

Large essays overwhelm a single image prompt. Polyptych Studio's bet is
**task decomposition**: split the journey from prose to picture into small,
inspectable, individually testable steps, keep each step model-agnostic, and let
the structured output of one stage become the precise input of the next. The
result is visual media that stays faithful to the source — one essay, many
coordinated panels.
