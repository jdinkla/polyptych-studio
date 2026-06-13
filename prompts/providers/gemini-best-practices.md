# Gemini Image Best Practices

Default model: `gemini-3.1-flash-image` — native Gemini image generation (not Imagen). Fast, cost-effective, with built-in reasoning. Continue using the Nano-Banana Pro methodology with these Gemini-specific optimizations.

## Nano-Banana Pro Format

Gemini responds well to the structured 9-section Nano-Banana Pro format already implemented in the system. Continue using:

1. **GOAL** - Overall objective and context
2. **SUBJECT** - Main visual elements
3. **COMPOSITION** - Layout and spatial arrangement
4. **SETTING** - Environment and background
5. **LIGHTING** - Light sources, direction, quality
6. **TEXT_ELEMENTS** - Text with quotes and placement
7. **STYLE** - Visual aesthetic and medium
8. **FIDELITY** - Quality and detail level
9. **CONSISTENCY** - Elements for visual coherence

## Prompting Style

Gemini's native image generation works best with **descriptive narrative paragraphs**, not keyword lists. A coherent paragraph describing the scene produces better, more coherent results than disconnected terms.

- For realistic images: incorporate photography terms — camera angles, lens types, lighting setups, fine details
- For illustrations: be explicit about artistic style, line work, shading approach
- The Nano-Banana Pro sections naturally provide this narrative structure

## Gemini Strengths

- **World knowledge**: Interprets cultural and contextual references well
- **Advanced text rendering**: Generates legible, stylized text for infographics, diagrams, and marketing assets
- **Multi-turn editing**: Iteratively refine images through conversational context
- **Reference images**: Supports up to 14 reference images (10 objects + 4 characters) for consistency
- **Abstract concepts**: Translates metaphorical descriptions effectively
- **Thinking mode**: Uses reasoning to work through complex prompts, generating interim test images before final output

## Text Rendering

Gemini 3.1 Flash has strong text rendering capabilities:

- Generates legible, stylized text directly in images
- Works well for infographics, menus, diagrams, marketing assets
- Keep text short and clear for best results
- Use common fonts (serif, sans-serif)
- Emphasize text importance in the prompt when it's critical
- For very complex multi-text layouts, consider visuals-only mode with overlay post-processing

## Aspect Ratios

Supported: 1:1, 1:4, 1:8, 2:3, 3:2, 3:4, 4:1, 4:3, 4:5, 5:4, 8:1, 9:16, 16:9, 21:9

## Resolution

Supports 512px, 1K, 2K, and 4K output resolutions. Use resolution hints in prompts (e.g., "suitable for 2K display") to guide quality.

## Quality Descriptors

Gemini responds to:

- "high quality", "detailed", "professional"
- "photorealistic" or specific art styles
- Specific photography/illustration terminology

## Consistency Guidance

For maintaining visual consistency across slides:

- Reference the design system's motif and color palette explicitly
- Include consistency reminders in each prompt
- Use the CONSISTENCY section to list recurring visual elements
- Reference images can enforce consistency when available

## Notes

- All generated images include SynthID watermarks identifying AI generation
- Safety filters apply; avoid prompts that violate Google's Prohibited Use Policy
