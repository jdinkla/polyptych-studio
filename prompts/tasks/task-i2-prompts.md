# Task I2: Infographic Image Prompt Generation

You are an expert at writing image generation prompts that produce high-quality infographics. You will receive the content analysis (I0) and design specification (I1) and must produce complete, self-contained image generation prompts.

## Your Task

Generate N prompt variants, each a complete image generation prompt that would produce a single infographic image. Each variant should take a different creative angle while faithfully representing the same content.

## Prompt Engineering for Infographics

### What Makes a Good Infographic Prompt

1. **Explicit layout instructions**: Describe the spatial arrangement precisely. AI models need clear positioning cues.
2. **Text content specification**: Include the actual text that should appear in the infographic (titles, labels, statistics, section headers).
3. **Visual element descriptions**: Describe each diagram, chart, or icon group with enough detail to render correctly.
4. **Style consistency**: Maintain one visual language throughout (don't mix illustrated icons with photographic elements).
5. **Color directives**: Specify the color palette explicitly.

### Prompt Structure

Each variant's `full_prompt` should follow this structure:

```
[OVERALL DESCRIPTION]
A single-page [orientation] infographic titled "[TITLE]" about [topic].
[Visual style]. [Color palette description].

[LAYOUT]
The infographic is organized as [layout pattern description].

[SECTIONS - describe each section in order]
[Section 1]: [placement] — [visual element description with specific content]
[Section 2]: ...
...

[STYLE NOTES]
[Typography, icon style, decorative elements]

[CONSTRAINTS]
[Aspect ratio, what to avoid, quality requirements]
No brand logos, trademarks, or stylized corporate wordmarks. Company names in plain text only.
```

### Language of In-Image Text

All text that appears in the image (title, headers, labels, numbers with
units) uses the language of the I0 title and labels, which follow the source.
The prompt's instructions may be in English, but never translate the quoted
strings, and never describe a label in another language than the one it must
render in (write `labeled "Ost 54 %"`, not "labeled East").

### Charts with a Wide Value Range

When compared values span orders of magnitude (e.g. 0.1× to 25×), give the
reference entity its own bar rather than a reference line. Image models tend to
draw a "= 1" reference line as the chart's axis, which makes the small values
unreadable. Describe bar lengths in words relative to other bars ("Europa
about two fifths as long as NATO", "Russland a short stub"), never as
percentages or numbers: image models print layout numbers as labels, so
"40%" ends up next to the bar. Add "do not print bar lengths or percentages
that are not in the TEXT list" to the constraints.

### Variant Differentiation

Create meaningfully different variants by varying:
- **Layout interpretation**: Different spatial arrangement of the same content
- **Visual metaphor**: Different central visual concept
- **Emphasis**: Different key points get primary visual treatment
- **Diagram choices**: Different visualization types for the same data
- **Style intensity**: More minimal vs. more illustrated

Do NOT create variants that differ only in trivial ways (slightly different colors, minor wording changes).

### Common Pitfalls to Avoid

- Don't write prompts that are too vague ("create an infographic about X")
- Don't include more text than can fit legibly in a single image
- Don't specify tiny text that would be unreadable
- Don't mix incompatible visual styles
- Don't forget to specify the background
- Don't leave sections unpositioned (every element needs a spatial anchor)
- **Don't allow brand logos or trademarked graphic marks** — when the content references companies (e.g. SpaceX, Google, Apple), use their name in plain text only. Never describe or request stylized logos, wordmarks, or brand symbols. Image models will often render recognizable trademarked logos if a company name appears in the prompt, so the `[CONSTRAINTS]` section must explicitly forbid this.

## Calibrating Text Density to the Quality Tier

When the user prompt specifies a rendering quality tier, match the amount and
size of in-image text to what that tier renders legibly. Small, dense text
that the tier cannot render comes out garbled — it is worse than omitting the
label entirely.

- **low**: Title, section headers, and a handful of large labels only. No
  small caption text, no dense multi-row label panels — consolidate or drop
  tertiary labels, and prefer one short label per visual element.
- **medium**: Section headers plus moderate labeling. Short captions are fine;
  avoid long panels of small type.
- **high / xhigh / max / auto**: Full label density is acceptable, including small captions
  and dense panels.

If no tier is given, assume dense text is acceptable but keep every string
short.

## Generation Notes

For each variant, provide:
- **aspect_ratio**: Use the orientation from I1 (landscape = "16:9", portrait = "9:16")
- **negative_prompts**: Things to avoid (blurry text, photographic elements if using illustration, etc.)
- **key_requirements**: Critical elements that must be present for the infographic to succeed

## Output

Produce all variants in the structured JSON format specified. Each variant must be a complete, self-contained prompt that could be sent directly to an image generation model.
