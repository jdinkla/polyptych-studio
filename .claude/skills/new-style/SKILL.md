---
name: new-style
description: Create a new visual style transfer preset for image generation pipelines
argument-hint: <preset-name> <creative-brief>
---

# Create Style Transfer Preset

## Role

You are a visual art director and prompt engineer. Your task is to create a new style transfer preset for the Polyptych image generation system.

## Context

Style presets live under `prompts/style-transfer/<category>/<preset-name>.md` as pure Markdown (no YAML frontmatter). They are loaded by stem name (e.g., `--style anime-dark` resolves to `prompts/style-transfer/anime/anime-dark.md`) and injected into image generation prompts. Categories present: `anime/`, `editorial/`, `infographic/`, `noir/`, `period-art/`.

## Arguments

- `$0` = preset name (kebab-case, e.g., `art-nouveau-botanical`)
- Remaining arguments = creative brief describing the desired aesthetic

If arguments are missing, ask the user for:
1. A short name (kebab-case)
2. A creative brief: genre, era, mood, key visual references, and intended use (slides, infographics).

## Process

1. **Read 2 existing presets** for calibration — one comprehensive and one lean:
   - Comprehensive: `prompts/style-transfer/noir/cinematic-illustrative-noir.md`
   - Lean: `prompts/style-transfer/anime/anime-dark.md` (~35 lines)
2. **Ask the user** whether they want a comprehensive or lean preset, if not obvious from the brief. Also decide the target category subdirectory (`anime/`, `editorial/`, `infographic/`, `noir/`, `period-art/`) — infographic styles go under `infographic/`, essay/slide styles under `editorial/`.
3. **Generate the preset** following the template below.
4. **Write it** to `prompts/style-transfer/<category>/$0.md`.
5. **Verify** it loads: run `uv run pixbridge style-transfer --list-styles` and confirm the new preset appears.

## Template Structure

Use the following sections. All are required unless marked (optional). Adapt section depth to match comprehensive vs lean choice.

```markdown
# {Preset Title} Style Transfer

## Visual Identity
One paragraph: the conceptual anchor. Name primary artistic/cinematic/cultural references.
State the core visual metaphor or principle.

## Core Aesthetic
- 4-6 bullet points defining the look
- Each bullet: a concrete visual rule, not a vague adjective
- Include rendering technique (e.g., "cel-shaded", "crosshatched", "tinted monochrome")

## Era & Setting (optional — include for scene-based or theatrical styles)
Default time period, architectural vocabulary, environmental types.
If included, list 4-8 key environment types with visual descriptions.

## Color Palette
**Base palette:**
- 4-6 named color groups with hex codes and semantic labels
- Format: `- **Label**: Description (#HEXVAL), secondary (#HEXVAL)`

**Accent colors:**
- 3-5 accent colors with hex codes and when to use them

**Palette rules:**
- 1-3 constraints (e.g., "never fully saturated", "70% dark tones")

## Lighting
- 4-6 lighting scenarios with names and descriptions
- Each: light source, direction, emotional meaning, technical rendering
- Describe shadow behavior

## Character Rendering (optional — skip for data/editorial styles)
- 3-5 character archetypes with rendering rules
- Include: face treatment, costume rules, level of stylization
- Describe how distortion/stylization varies by character role

## Texture & Fidelity
- Physical surface quality (film grain, paper texture, digital precision, etc.)
- Medium simulation (what does this look like it was made with?)
- Detail distribution (where is detail dense vs sparse?)

## Composition
- 4-6 compositional rules with names
- Framing logic, spatial relationships, scale preferences
- How the style organizes visual information

## Mood & Tone
1-2 paragraphs: the emotional register.
What does the viewer feel? What subtext runs beneath every image?
The tension or paradox that gives the style its character.

## Storytelling Function (optional — include for story-driven styles)
How each image serves the story. What role does the visual style play in meaning-making?

## Text Treatment (optional — include if typography matters)
- Font families or historical type references
- Text placement conventions
- How text integrates with the image

## Key Phrases for Prompts
- 8-12 short phrases (quoted) that can be dropped into image generation prompts
- Each captures a core visual quality
- Mix technical and evocative language

## Influence Direction (implicit)
List primary references: films, artists, movements, techniques, specific works.
These guide the aesthetic without requiring literal imitation.

## Avoid
- 8-15 bullet points: what this style is NOT
- Be specific (not "bad quality" but "clean corporate AI aesthetics")
- Include adjacent styles that could contaminate this one
```

## Quality Checks

Before writing the file, verify:
- [ ] All hex codes are valid 6-digit hex (#RRGGBB format)
- [ ] Color palette has semantic labels, not just hex values
- [ ] "Avoid" section includes at least 8 items
- [ ] Key phrases are concrete enough to copy-paste into a prompt
- [ ] No generic AI art language ("stunning", "breathtaking", "masterpiece")
- [ ] Style has a clear identity that distinguishes it from existing presets
- [ ] File name matches the `$0` argument in kebab-case

## Naming Convention

- Use kebab-case: `art-nouveau-botanical.md`
- Include era if relevant: `1920s-bauhaus-industrial.md`
- Include medium if distinctive: `woodblock-ukiyo-e.md`
- Use `_v2` suffix only for revisions of existing presets
