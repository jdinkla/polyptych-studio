---
name: trace-prompt
description: Trace a generated image backwards through the pipeline to find where visual issues originated
argument-hint: <output-directory> <item-number>
---

# Prompt Trace — Diagnose Image Generation Issues

## Role

You are a visual pipeline debugger. Given an output directory and a specific image number, trace the image backwards through the entire pipeline chain to find where a visual issue was introduced — was it the image model, the prompt, the shot plan, the character description, or the source text?

## Arguments

- `$0` = output directory (e.g., `generated/3`)
- `$1` = image/frame/scene/slide number (e.g., `42`)

If arguments are missing, ask for both.

## Process

### Step 1: Detect Pipeline Type and Load Image

Determine the pipeline from files present:

| Pipeline | Signal File | Image Pattern | Prompt Pattern |
|----------|-------------|---------------|----------------|
| Slide | `task4-content.yaml` | `images/slide-{NN}.{ext}` | `prompts/slide-{NN}-prompt.yaml` |
| Infographic | `task-i2-prompts.yaml` | `images/infographic-v{N}.{ext}` | (embedded in task-i2) |

**Read and display the target image** so you can see what the user is asking about.

Also read `manifest.yaml` first if present (per CLAUDE.md "Reviewing generated outputs") — it records the resolved style preset, provider/quality, and, for locally produced directories (`mode: local`), which text tasks Claude generated (`tasks_completed`) and the `style_prompt` that shaped the prompts.

### Step 2: Trace the Pipeline Chain (bottom-up)

Work backwards from the image. For each layer, read the relevant file and extract the data that fed into the next layer.

#### Slide Pipeline (full chain):

```
Layer 0: IMAGE
  → Read: images/slide-{NN}.{ext}
  → Display the image

Layer 1: PROMPT
  → Read: prompts/slide-{NN}-prompt.yaml
  → Extract: full_prompt, sections, characters_in_frame (fiction), text_elements
  → Look for: What did the prompt actually ask the image model to generate?

Layer 2: SLIDE SPEC
  → Read: task6-slides.yaml (find slide NN)
  → Extract: headline/quote, scene_beat, characters_in_frame, callout
  → Look for: Was the per-slide content specified correctly?

Layer 3: CONTENT
  → Read: task4-content.yaml (find slide NN)
  → Extract: allocated paragraphs / source_paragraphs, body_text
  → Look for: Was the right source material allocated to this slide?

Layer 4: DESIGN
  → Read: task5-design.yaml (visual system, palette, callout_treatment)
  → Look for: Does the design system conflict with the slide's intent?

Layer 5: STRUCTURE → task3-structure.yaml (section boundaries, slide count)
Layer 6: ANALYSIS → task2-analysis.yaml (incl. character_canon for fiction)
Layer 7: GENRE → task1-genre.yaml
Layer 8: SOURCE → source.md (the paragraph(s) referenced by the slide)
```

#### Infographic Pipeline:

```
Layer 0: IMAGE → images/infographic-v{N}.{ext}  (display it)
Layer 1: PROMPT → task-i2-prompts.yaml (find variant N; full_prompt + sections)
Layer 2: DESIGN → task-i1-design.yaml (visual_style, color_palette, content sections)
Layer 3: ANALYSIS → task-i0-analysis.yaml (primary key points, visualizable_data, source_paragraphs)
Layer 4: SOURCE → source.md (the paragraph(s) referenced by i0)
```

### Step 3: Identify the Fault Layer

After tracing, identify WHERE the issue was introduced:

| Fault Layer | Symptom | Typical Fix |
|-------------|---------|-------------|
| **Image model** | Prompt is correct but image doesn't match | Regenerate with different provider or seed |
| **Prompt** | Prompt contains wrong/contradictory instructions | Fix prompt generation task (task7 / i2) |
| **Slide spec / design** | Wrong per-slide content or conflicting visual system | Fix task6 / task5 (slide); i1 (infographic) |
| **Content allocation** | Wrong source material on this slide | Fix task4 (slide) |
| **Analysis** | Key point or data point wrong/missing | Fix task2 (slide) / i0 (infographic) |
| **Character desc (fiction)** | Character looks wrong, details missing | Fix `character_canon` in task2, re-embed in task7 |
| **Structure** | Section boundaries / slide count wrong | Fix task3 (slide) |
| **Source text** | Source is genuinely ambiguous | Note limitation, consider source edit |

### Step 4: Present Findings

Format as a diagnostic report:

```
## Prompt Trace: slide-04 in generated/my-essay

### Image
[displayed above]

### Issue
[User's description of what's wrong, or your observation]

### Trace
| Layer | File | Key Data | Status |
|-------|------|----------|--------|
| Image | slide-04.png | — | [issue visible here] |
| Prompt | slide-04-prompt.yaml | "diagram with three arrows..." | OK / PROBLEM |
| Slide Spec | task6 slide 4 | "callout: three drivers" | OK / PROBLEM |
| ... | ... | ... | ... |

### Root Cause
**Fault layer:** [e.g., "Prompt generation — task6 names 'three drivers' but task7's prompt only describes two, so the image shows two labeled arrows and one blank"]

### Recommended Fix
[Specific action: which task to rerun, what to change in the prompt/description, or whether to just regenerate the image]
```

### Step 5: Suggest Fix Command

Based on the fault layer, suggest the appropriate action:

- **Image model fault (slide):** `just gen deck SOURCE --output-dir OUTPUT --style STYLE --image-preset gem --from images --slides "4"` (try a different provider via `--image-preset xai` or `--image-preset openai-low`)
- **Image model fault (infographic):** `just gen infographic SOURCE --output-dir OUTPUT --style STYLE --image-preset openai-high --from images`
- **Prompt fault:** Re-run the prompt task locally with `/run-local-task task7 OUTPUT` (slide) or `/run-local-task i2 OUTPUT` (infographic), then regenerate images
- **Slide-spec / design fault:** Edit or re-run task6 / task5 (slide) or i1 (infographic), e.g. `/edit-output OUTPUT task6 "..."`, then re-run downstream
- **Analysis / structure fault:** Re-run from the earliest affected task (task2/task3 for slide, i0 for infographic) via `/run-pipeline ... --from <step>`

## Notes

- When comparing across layers, pay attention to CHARACTER NAMES (fiction slide decks) — a common issue is anonymous references ("a young woman") replacing named characters from `character_canon`
- Spatial directions (left/right/facing) and counts (e.g. "three drivers") are frequent sources of confusion between the slide/infographic spec and what the image model renders
- For the infographic pipeline, if the i2 critique/refine pass ran, compare the prompt before and after refinement to see whether the critic introduced or fixed the issue
