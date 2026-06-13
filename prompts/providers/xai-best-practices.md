# xAI Grok Image Best Practices

When generating prompts for xAI's Grok image generation, apply these guidelines. Grok uses an OpenAI-compatible SDK, so many OpenAI best practices apply.

## Compatibility with OpenAI Practices

Since Grok uses OpenAI's SDK interface, apply similar prompt engineering techniques:

- **Camera terminology**: Use lens, aperture, and lighting language
- **Explicit composition**: Describe framing, angles, and spatial relationships
- **Text in quotes**: Put all text content in exact quotes
- **Medium references**: Specify photography style or visual medium

## Text Rendering

Follow OpenAI-style text instructions:

- **Quote exactly**: `"Your Text Here"`
- **Placement precision**: "centered bottom third", "upper-left corner"
- **Font guidance**: "bold serif", "clean sans-serif", "elegant display font"
- **Verbatim request**: "render text exactly as written"

## Photography Language

Use camera and photography terms:

- **Lens**: "35mm lens", "85mm portrait lens", "wide-angle"
- **Aperture**: "f/2.8 shallow depth of field", "f/8 sharp throughout"
- **Lighting**: "golden hour", "soft diffuse light", "dramatic side lighting"

## Composition

Be explicit about visual arrangement:

- **Shot types**: "close-up", "medium shot", "wide establishing"
- **Angles**: "eye-level", "low-angle", "overhead"
- **Rules**: "rule of thirds", "centered symmetry", "leading lines"

## Style Guidance

Specify the visual aesthetic:

- "professional photography"
- "cinematic film still"
- "editorial magazine style"
- "technical illustration"

## Quality and Fidelity

Include quality indicators:

- "high quality", "detailed", "professional grade"
- "suitable for presentation slides"
- "clean and polished aesthetic"

## Example Structure

Follow the Nano-Banana Pro structure with OpenAI-style language:

```
GOAL: Professional presentation slide visual.

SUBJECT: [Main visual elements with descriptive detail]

COMPOSITION: Shot with 35mm lens, rule of thirds composition,
subject positioned on left intersection point.

LIGHTING: Soft diffuse natural light from upper left,
warm color temperature.

TEXT: Render exactly: "Headline Text" - large bold serif,
centered in upper third with subtle drop shadow.

STYLE: Editorial photography, professional and polished.

FIDELITY: High quality, suitable for 2K display.
```

## Notes

- xAI's image generation capabilities may differ from OpenAI's
- Test prompts and adjust based on actual results
- Monitor xAI documentation for Grok-specific guidance as it evolves
