# OpenAI GPT Image Best Practices

When generating prompts for OpenAI's GPT Image model family, apply these guidelines to optimize image quality, text rendering, and spatial composition.

> **Active model**: `gpt-image-2` (see `image_model_config.yaml`). The guidance below assumes gpt-image-2; differences from older `gpt-image-1` / `gpt-image-1.5` are noted inline.

## What's New in gpt-image-2

gpt-image-2 is materially better than the 1.x line at three things this pipeline relies on every day. Tune prompts to exploit them:

- **In-image text rendering** — small, dense, and stylized text is much more reliable. Use it confidently for slide titles, infographic labels, equation captions, sign text, and quoted body copy.
- **Spatial reasoning** — relational language ("behind the lectern", "on the table to the left of the laptop", "in the foreground, partially occluded by the doorway") is honored. Prior models routinely got "behind / in front of / on / left / right" wrong; with gpt-image-2 they work. Be explicit.
- **Complex composition & dense detail** — multi-object scenes, layered foreground/midground/background, and intricate diagrams hold together at higher fidelity.

Other gpt-image-2 changes worth knowing:

- **No `input_fidelity` parameter** — input images are processed at high fidelity automatically.
- **Flexible resolutions** — any size with both edges multiples of 16, max edge ≤3840px, total pixels ≤8.3M, ≤3:1 aspect ratio. (Older GPT Image models had fixed presets.)
- **Quality tiers** — `low` / `medium` / `high` / `auto`. Fixed-token cost model; `high` no longer disproportionately expensive.
- **Transparent backgrounds are not supported** for gpt-image-2 (use `background: opaque` or `auto`).

## Prompt Ordering for gpt-image-2

OpenAI recommends a consistent left-to-right order. The Nano-Banana Pro 9-section template the slide pipeline uses already aligns with this — when generating for OpenAI, order sections like so:

1. **Scene / setting / background** (where are we?)
2. **Subject** (what is the focal element?)
3. **Spatial relationships** (how do the elements relate — behind, in front of, on, beside?)
4. **Composition** (camera angle, framing, depth)
5. **Lighting / materials / mood**
6. **Text elements** (verbatim, quoted)
7. **Style / medium / fidelity**
8. **Constraints** (preserve list, negative prompts)

Repeat the preserve-list constraints on every prompt to reduce drift across iterative regenerations.

## Spatial Composition (gpt-image-2 strength)

This is where gpt-image-2 most outperforms prior models. Be explicit and concrete with relational language. Treat every multi-object scene as an opportunity to specify:

- **Depth ordering**: "in the foreground", "in the midground", "in the background", "behind X", "in front of X", "partially occluded by X"
- **Surface placement**: "on the table", "resting on the desk", "stacked atop the books", "leaning against the wall"
- **Lateral position**: "to the left of X", "to the right of X", "between X and Y", "centered between X and Y"
- **Containment**: "inside the box", "emerging from the doorway", "framed by the window"
- **Scale relative to neighbors**: "twice the height of the lectern", "small enough to fit in the palm"

For slide prompts, populate the dedicated `spatial_relationships` section in the output schema (alongside `composition`) with one or two sentences enumerating the explicit relationships. For free-text image prompts (infographic), inline this language in the prompt directly.

## Text Rendering (gpt-image-2 strength)

gpt-image-2 reliably renders short text strings, including stylized typography. To get clean output:

- **Quote literal text exactly**: put text content in straight double quotes — `"The Difficult Path"`, `"AMATEUR RADIO CLUB - W6HAM"`. Both `"Quoted"` and `ALL CAPS` work; pick one form per prompt and stick with it.
- **Spell out tricky words letter-by-letter** for brand names, technical jargon, or uncommon spellings: `"K-U-B-E-R-N-E-T-E-S"`, `"S T R O M B O L I"`.
- **Specify exact placement** with the spatial-language vocabulary above:
  - "top-right corner", "centered in bottom third", "left-aligned on upper quarter"
  - "overlaid on lower-left with 20% margin from edges"
- **Describe font characteristics**: "bold serif typeface", "clean sans-serif", "elegant script", "large display font", "small caption text"
- **Specify text hierarchy**: "headline in large bold, body text in medium weight below"
- **Request verbatim rendering**: "render text exactly as written, no additional characters or modifications"
- **Use medium or high quality** for small or dense text panels — `low` is fine for large, simple titles.

## Photorealism & Camera Terminology

Instead of generic quality terms like "8K" or "ultra-detailed", use camera and photography language:

- **Lens specifications**: "shot with 35mm lens", "85mm portrait lens", "wide-angle 24mm"
- **Aperture and depth**: "f/2.8 aperture with shallow depth of field", "f/11 for sharp foreground to background"
- **Lighting conditions**:
  - "golden hour sunlight", "soft diffuse window light", "dramatic side lighting"
  - "studio lighting with soft boxes", "natural overcast daylight"
  - "warm incandescent interior lighting"
- **Camera effects**: "background bokeh", "motion blur on moving elements", "lens flare from light source"

For non-photographic images, drop the camera vocabulary — gpt-image-2 honors "photorealistic" only when you say so explicitly. For illustration, infographic, or anime styles, name the medium directly ("flat vector illustration", "watercolor on textured paper", "1990s anime cel with hand-drawn linework").

## Visual Medium References

Be explicit about the visual medium and style:

- **Photography styles**: "professional studio photography", "editorial magazine photography", "documentary-style candid shot", "lifestyle photography"
- **Cinematic references**: "cinematic film still", "movie poster composition", "widescreen cinematic framing"
- **Technical illustration**: "technical diagram style", "architectural visualization", "infographic illustration"

## Composition Guidelines

Be explicit about framing and composition:

- **Shot types**: "extreme close-up detail shot", "medium close-up portrait", "wide establishing shot", "top-down flat lay composition", "three-quarter view"
- **Perspective and angle**: "eye-level perspective", "low-angle heroic shot looking up", "high-angle overview", "Dutch angle for tension"
- **Compositional rules**: "rule of thirds with subject on left intersection", "centered symmetrical composition", "leading lines drawing eye to focal point", "negative space on right for text placement"

## Color and Mood

- **Color palette guidance**: "warm earth tones", "cool blue-gray palette", "high contrast black and white"
- **Mood descriptors**: "contemplative and serene", "energetic and vibrant", "moody and atmospheric"
- **Contrast levels**: "high contrast dramatic", "low contrast soft", "balanced midtones"

## Quality, Size & Cost

- **Quality**: `low` for drafts and high-volume runs, `medium` as a default, `high` for text-heavy slides / infographics / final assets, `auto` to let the model pick. The slide and infographic pipelines both default to `high` on OpenAI.
- **Recommended sizes** (both edges divisible by 16, aspect ratio within [1:3, 3:1], max edge ≤3840px):
  - `1024x1024` — square
  - `1024x1536` — HD portrait
  - `1536x1024` — HD landscape
  - `2048x1152` — true 16:9 landscape
  - `2560x1440` — QHD landscape (reliability boundary; above this is experimental)
  - `3840x2160` — 4K landscape (experimental)
- Outputs above 2560×1440 may take up to ~2 minutes per image and cost notably more.

## Iteration Strategy

- Iterate instead of overloading. Long prompts work, but debugging is easier when you start with a clean base prompt and refine with small, single-change follow-ups.
- Re-specify critical details (style, identity, spatial layout) on every iteration if they start to drift.
- For multi-image series (slide decks, anime shots, infographic variants), name the consistent style explicitly on every prompt, not just the first.

## GPT Image Architecture Notes

GPT Image uses an autoregressive architecture (same as the LLM), which means:

- It excels at following complex, detailed instructions
- Multi-step prompts with clear structure work well
- It can handle nuanced creative direction
- Text rendering and spatial reasoning benefit from explicit instruction

## Example Prompt Structure (gpt-image-2)

```
SCENE: A small university radio booth at dusk, warm desk lamp glow, dark wood-paneled
walls, vintage equipment racks visible in the background.

SUBJECT: A weathered leather journal open on the desk, brass fountain pen resting
across the pages.

SPATIAL RELATIONSHIPS: The journal sits centered on the desk, in the foreground.
A vintage tube radio is positioned behind it and slightly to the right, partially
occluded by the desk lamp. A coffee mug rests to the left of the journal, on the
same surface, in front of a stack of three books that lean against the wall.

COMPOSITION: Three-quarter overhead angle, rule of thirds with journal on left
intersection points. Shallow depth of field — journal sharp, radio softly out of
focus. Shot with 85mm lens at f/2.8.

LIGHTING: Warm desk-lamp light from upper-left, ~3200K. Soft shadows pooling to the
right of each object. No harsh highlights.

TEXT: Render exactly "The Difficult Path" in elegant serif font, large and bold,
positioned in the upper-right third of the frame with subtle drop shadow for
legibility against the dark wall.

STYLE: Editorial magazine photography, lifestyle aesthetic, restrained.

CONSTRAINTS: No watermark, no extra text, preserve the spatial layout and warm
color temperature exactly as described.
```
