# Pipeline Architectures: Infographic

This document covers the architecture of the **infographic** pipeline and the image-generation infrastructure it shares with the slide pipeline. For the slide pipeline's task structure, see [System Overview](system-overview.md) and [Task Decomposition](task-decomposition.md).

## Pipeline Comparison

| | Slide | Infographic |
|---|---|---|
| Steps | 8 (`task1`–`task7` + images) | 4 (`i0`–`i2` + images) |
| Source type | Any text | Any text |
| Output | Slide deck images | Single-page infographic variants |
| Parallelism | Optional concurrent image generation (`--concurrent`) | None |
| Critique/refine | No | Optional on `i2` (`--critique`, off by default) |

## Shared Infrastructure

### ImageBatchGenerator (image generation engine)

`src/polyptych/image_batch.py` — the single image-batch-generation engine behind both pipelines' `images` step. Each pipeline composes an `ImageBatchGenerator` with a few variation points:

- **`label`** — the item noun ("slide", "variant") used in progress lines and failure reports; the output filename is always `{item_id}{suffix}` (e.g. `infographic-v1.png`).
- **`build_prompt` hook** — converts the pipeline's prompt payload into a provider-ready `ImagePrompt`. Pipeline-specific assembly lives here (e.g. attaching reference images and routing through `generate_image_with_optional_refs` when refs are present).
- **`client_factory`** — binds `_make_image_client(provider)`; concurrent mode constructs one `ImageClient` per consumer thread.

The engine owns everything the pipelines would otherwise duplicate: skip-existing checks (`{item_id}.*` glob), `--force`, per-item failure isolation (`(index, "ExceptionType: message")` capture, run continues), renaming, and generated/failed/skipped reporting. It provides three execution shapes:

1. **Sequential** (`run_sequential`) — one item at a time.
2. **Interleaved** (`run_interleaved`) — pulls N prompts from an LLM-backed generator, generates their images, then pulls the next N (slide `--interleave`).
3. **Concurrent** (`run_concurrent`) — wraps `ConcurrentPipelineEngine` (producer-consumer with a bounded queue). Work items carry resume logic: `build_preloaded_work_items` for images-only runs (prompts already on disk), `build_resumable_work_items` for full runs (skip items with prompt + image; preload prompt-only items so consumers run without an LLM call). Prompt generation stays a pipeline-supplied `produce_fn` closure.

The infographic pipeline runs sequentially — it produces only a handful of variant images, so concurrency adds little. The slide pipeline uses all three shapes depending on `--concurrent` / `--interleave`.

---

## Infographic Pipeline

**Purpose:** Generate single-page infographic images from any source text. Produces N design variants for selection.

### Step Sequence

| Step | Task | Description | Depends on |
|------|------|-------------|------------|
| `i0` | Content analysis | Key points, relationships, data, structural patterns | Source text |
| `i1` | Design specification | Layout, sections, color palette, visual style | I0 |
| `i2` | Image prompts | N variant prompts (default 3, range 1–5) | I0, I1 |
| `images` | Image generation | N infographic images | I2 |

When `--critique` is set, the `i2` step runs an optional critique-refine loop (`i2_critique` → `i2_refine`) before image generation. See [Critique/Refine Pattern](critique-refine-pattern.md).

### Data Flow

```
source.md
  │
  ▼
 [I0] content analysis
  │
  ▼
 [I1] design spec
  │
  ▼
 [I2] N prompt variants ──→ [images] N infographic images
       │
       └─ (optional) i2_critique → i2_refine   when --critique
```

### Key Architectural Details

**Strictly linear.** No parallelism — each step depends on all previous steps.

**Variant generation.** I2 produces `--variants` (default 3) alternative infographic prompts from the same analysis and design spec. Each variant explores a different visual approach; the user selects across them.

**Provider-aware prompts.** I2 loads provider-specific best-practice guidelines from `prompts/providers/` to optimize prompts for the target image generation provider.

**Optional critique.** Off by default. With `--critique`, I2 prompts are audited against the I0 content analysis (coverage), the I1 design spec (entity/color consistency, flow), and the rendering quality tier (text density) before the expensive image step. `--critique-rounds N` controls iteration count (default 1); refinement exits early when a round finds no critical/important issues.

**Source-agnostic.** Works on any source text — essays, technical documents, reports.

### Output

Images are named `infographic-vN.{ext}` where N is the variant number (1-indexed).

---

## Related Documentation

- [System Overview](system-overview.md) — slide pipeline architecture
- [Critique/Refine Pattern](critique-refine-pattern.md) — detailed guide to the i2 critique loop
- [Multi-Agent Patterns](multi-agent-patterns.md) — abstract patterns (Sequential Pipeline, Generator-Critic, Fan-Out/Gather)
- [CLI Reference](../reference/cli-reference.md) — full command and flag documentation
