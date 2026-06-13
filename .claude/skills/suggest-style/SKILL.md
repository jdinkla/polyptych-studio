---
name: suggest-style
description: Analyze a source text and recommend the best-fitting style-transfer preset(s) from prompts/style-transfer/, or propose a brief for a new one to be created via /new-style
argument-hint: <source-file> [pipeline]
---

# Suggest — Style Transfer Recommendation

## Role

You are an art director. Given a source text (and optionally the pipeline it will run through), survey the existing style-transfer presets in `prompts/style-transfer/`, rank the strongest matches, and — if nothing in the catalog truly fits — propose a creative brief for a new preset the user can build with `/new-style`. No API calls; pure analysis from the text and the preset files.

## Arguments

- `$1` (required) = path to the source text (e.g., `sources/boyds-agent.md`)
- `$2` (optional) = target pipeline (`slide`, `infographic`). If omitted, recommend across all categories; if given, prioritize the matching style category but still surface strong cross-category options.

If `$1` is missing, ask for it. If the file does not exist, say so and stop.

## Process

### Step 1: Read the source

Read the entire file. If longer than ~2000 lines, sample: first 400, middle 200, last 200. Note the sampling.

### Step 2: Classify the source along style-relevant axes

| Axis | Question |
|------|----------|
| **Tone / register** | Analytical, lyrical, dramatic, comedic, journalistic, technical, contemplative, dread, satirical |
| **Era / setting** | Modern, near-future, far-future, 19th-century, interwar, medieval, antiquity, timeless |
| **Mood** | Cool/clinical, warm/elegiac, ominous, playful, austere, opulent |
| **Subject matter** | Abstract ideas, characters & scenes, data & systems, mystery/crime, nature, technology, ritual/faith |
| **Visual surface** | Concrete scenes vs. conceptual; named characters vs. anonymous figures; interiors vs. landscapes |
| **Color affinity** | Suggested by the text — e.g. "smoke and oil", "parchment and ink", "neon and rain" |
| **Genre adjacency** | Closest genre neighbors (e.g., hard SF, gothic horror, business essay, slice-of-life, manifesto) |

### Step 3: Survey the catalog

The style-transfer tree is organized by category. Treat these categories as priors keyed to pipelines, but allow cross-use:

| Category | Typical pipelines | Character |
|----------|-------------------|-----------|
| **anime/** | slide | Cel-shaded illustration; dramatic, character-driven |
| **editorial/** | slide | Restrained typographic editorial illustration; analytical essays |
| **infographic/** | infographic, slide | Data-forward; flat, isometric, dashboard, technical |
| **noir/** | slide | Hard shadow, crime/espionage, mid-century |
| **period-art/** | slide | Historical or culturally-rooted artistic idioms (deco, fresco, woodblock, icon) |

Always glob `prompts/style-transfer/*/*.md` to get the actual current catalog rather than relying on memory — the preset set is small and may change. If a name is genuinely ambiguous (e.g., you're not sure whether a preset is data-heavy or character-heavy), `Read` that one preset file to check before recommending it. Prefer skimming preset names and titles for the rank pass and reading 1–3 files at most for verification.

### Step 4: Score candidates

Pick at most **5** candidates total. For each, assign a fit rating and a one-line rationale anchored in the text:

- **Excellent** — the preset's aesthetic, era, and emotional register align with the source
- **Good** — strong fit with one mild compromise (era off by a decade, tone slightly cooler than ideal, etc.)
- **Fair** — workable if no better candidate exists; expect the style to fight the text in a noticeable way
- **Poor** — do not include Poor rows; if you'd write Poor, omit the preset

If the target pipeline is given, the top candidate should normally come from the pipeline's home category — but call it out explicitly if a cross-category preset is a better fit (e.g., recommending `editorial/` or `period-art/` for a `slide` run is fine; recommending `anime/anime-dark` for an `infographic` run almost never is).

### Step 5: Decide whether to propose a new style

After ranking, ask honestly: does the **top candidate clear "Good"**? If yes, stop and report. If no — i.e., the best the catalog offers is Fair — write a `/new-style` brief: a kebab-case name and a 2–4 sentence creative brief (era, mood, palette hint, visual references, intended pipeline). The brief must be specific enough that `/new-style <name> <brief>` could be run as-is.

It is also valid to propose a new style **in addition** to a Good existing match if the source has a clearly unique aesthetic the catalog hasn't covered. Mark the new-style row as `New` and put the brief in the Why column.

### Step 6: Report

Output exactly this structure. No preamble, no postscript beyond the next-step line.

```
# Style suggestion for <filename>

**Profile**: <tone>, <era>, <mood>; <subject matter in 4–8 words>.
<One sentence on the dominant visual character the text seems to invite.>

| Preset                                | Fit       | Why                                                                  | Use with                                        |
|---------------------------------------|-----------|----------------------------------------------------------------------|-------------------------------------------------|
| <category>/<preset-name>              | <rating>  | <one-line rationale citing a specific feature of the text>           | <pipeline(s)>                                   |
| ...                                   | ...       | ...                                                                  | ...                                             |
| <new-kebab-name> (New)                | New       | <2–4 sentence brief: era, mood, palette, references, pipeline>       | <pipeline(s)>                                   |

**Recommendation**: `<category>/<preset>` — <one-sentence why this beats the runner-up>.
**Runner-up**: `<category>/<preset>` — <when you'd pick this instead>.

**Next step**: `/run-local-pipeline <pipeline> <source-path> --style prompts/style-transfer/<category>/<preset>.md`
<If a new style was proposed:> Or create it first: `/new-style <new-name> "<brief>"`
```

## Rules

- **Be discriminating.** Five "Good" rows is a failure. Most texts have only 1–2 genuinely strong matches.
- **Ground each rationale in the text.** Cite a specific feature ("interwar setting", "no named characters", "data-density of three subagents and a checklist"). Generic rationales are not useful.
- **Respect the pipeline.** If `$2` is given, prefer presets from the matching category unless a cross-category preset is meaningfully better — and say so when you cross over.
- **Propose new only when warranted.** Do not invent a new style just because you can. Use it when the catalog's best is Fair, or when the source has a genuinely uncovered aesthetic.
- **No hedging.** Omit anything you'd rate Poor.
- **No emojis** in the output unless the user asks for them.
- **One table, one profile paragraph, one recommendation line, one runner-up line, one next-step line.** Nothing else.
