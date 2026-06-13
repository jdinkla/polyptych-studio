# Write Style Prompts

Both pipelines accept `--style PATH`, pointing at a style-transfer markdown preset under `prompts/style-transfer/`. The preset's directives are folded into image-prompt generation so every image in the run shares a coherent visual aesthetic. This guide covers how to write a preset that actually bites — image generators have strong defaults, and a weak preset gets ignored.

If a sibling image (`<name>.png` / `.jpg` / `.jpeg` / `.webp`) sits next to `<name>.md`, it is auto-prepended to the reference list as a visual exemplar for providers that support reference images (`openai` gpt-image-2, `gemini`). A good exemplar image is often worth more than another paragraph of prose.

## The Core Problem

Image generators have strong training-distribution defaults. When you name a broad style ("noir," "editorial," "vintage"), the generator reverts to the most common rendering of that label unless you fight it with specificity, repetition, and explicit negation. A directive like "muted colors" is treated as a suggestion; "near-monochrome, no saturated colors anywhere" is a constraint.

## Do's

### Be specific about what you mean

- **Name concrete references.** "1940s RKO film-noir cinematography" is stronger than "noir." "Swiss International Typographic Style" is stronger than "clean infographic." Generators and the LLM prompt pipeline both respond better to named anchors.
- **Describe the visual properties explicitly.** "High-contrast chiaroscuro, hard key light, deep blacks crushed to ink" beats "dramatic lighting." For an infographic: "flat vector shapes, 2px consistent stroke weight, generous whitespace, single accent hue."
- **Quantify where possible.** "Two-color palette plus one accent" is more constraining than "limited palette."

### Fight defaults with explicit negation

- The **Avoid** section is as important as the positive descriptions. Tell the generator what NOT to do. The preset's Avoid list is also pushed into the prompt's negative-prompt directives.
- Be redundant on purpose: state a constraint in the positive description AND in the Avoid list. The prompt is processed at multiple stages; repetition helps.
- Name the specific traditions you're rejecting ("no glossy 3D render, no stock-photo realism, no gradient meshes").

### Control lighting and texture deliberately

- Lighting drives mood more than almost anything else. Specifying "faces partially obscured, lit from below" or "even flat technical-illustration lighting" steers the result far more reliably than naming a mood word.
- Texture cues ("paper grain, halftone dots, visible brushwork" vs. "clean digital vector") prevent the generator from drifting toward its default rendering style.

### Include a short version

- The short version is what actually gets embedded in each per-image prompt. It needs to be dense and front-loaded with the most important directives.
- Lead with the style anchor, then setting/atmosphere, then secondary flavor. "1940s film-noir illustration, ink-wash rendering" should come before mood adjectives.

### Keep it generic

- A style preset should work with ANY source fed through the pipeline. Don't name source-specific characters, locations, or plot points — the pipeline fills in the specifics from the source analysis.
- Use period/setting and rendering directives for the look; let the content come from the pipeline.

## Don'ts

### Don't trust soft language

- "Muted" or "elegant" or "professional" are nearly meaningless to a generator. Be concrete about hue, contrast, geometry, and texture.
- Positive descriptions alone are insufficient. "Heavy ink linework" still needs "NOT clean digital vector lines."

### Don't mix incompatible influences

- Citing two references without specifying WHICH ASPECT of each creates confusion. Be precise: "the geometric layout discipline of Swiss design, but with hand-drawn iconography, not photographic imagery."

### Don't forget the rendering directive

- Subject and composition alone aren't enough. Specify the rendering style (hatching vs. gradients, flat vector vs. painted, cel-shaded vs. photographic) as its own concern, or the generator picks its default.

### Don't over-specify color

- Hex codes in style prompts are aspirational — generators don't honor them precisely. Describe color in relationships and restrictions ("near-monochrome with a single warning-red accent," "no saturated colors anywhere") rather than exact values. (The slide pipeline's task5 design step does carry hex palettes through to the prompt separately; the *style preset* should stay relational.)

### Don't make the prompt too long

- There's a practical limit to how much text influences generation. Front-load the critical directives; put atmospheric flavor after. The short version should capture ~80% of the intent in 2-3 sentences.

## Testing a New Style Preset

1. Run a small, cheap sample first — for the slide pipeline, `--from images --slides 1,5,10 --image-preset openai-low`; for the infographic pipeline, `--variants 2 --image-preset openai-low`.
2. Check whether the generator honored your Avoid list — defaults usually leak there first.
3. Compare against the references you cited. If the output doesn't read as belonging to that style, strengthen the named anchors and the negation language.
4. Iterate on the short version specifically — it is what reaches the per-image prompt.

## Related

- [CLI Reference](../reference/cli-reference.md) — the `--style` flag and the sibling-image convention
- [Task Decomposition](../explanation/task-decomposition.md) — how the slide pipeline's task5/task7 fold style into image prompts
