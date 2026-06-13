"""Task 7: Image Prompt Generation."""

from ..client import TextClient
from ..models import (
    CharacterSheet,
    ImagePrompt,
    ImagePromptDraft,
    ImagePromptSections,
    SlideImagePrompt,
    SlideSpec,
    Task1Output,
    Task5Output,
    Task6Output,
    Task7Draft,
    Task7Output,
)
from ..prompt_loader import load_task_prompt, load_provider_guidelines
from ..text_utils import dump_yaml


# Layout-specific text placement guidelines
LAYOUT_TEXT_PLACEMENT = {
    "split_horizontal": {
        "headline": "large serif bold, drop shadow, bottom-left (40% width)",
        "body": "medium serif, bottom text area (60% width)",
    },
    "split_vertical": {
        "headline": "large serif bold, text column top",
        "body": "medium serif, text column below headline",
    },
    "full_bleed": {
        "headline": "large white serif bold, drop shadow, lower third left-aligned",
        "body": "medium serif, lower third below headline",
    },
    "typography_focused": {
        "headline": "extra-large serif bold, centered, drop shadow",
        "body": "medium serif, centered below headline",
    },
    "comparison": {
        "headline": "large serif bold, top center spanning both halves",
        "body": "medium serif, in respective columns",
    },
    "infographic": {
        "headline": "large serif bold, text column top",
        "body": "medium serif, text column",
    },
}


# Fallback callout treatment when the task5 design system does not define one
# (special_techniques entry "callout_treatment" with a visual_spec).
DEFAULT_CALLOUT_TREATMENT = (
    "visually distinct boxed pull-quote, bold accent-color treatment, "
    "set apart from body text"
)


def resolve_callout_treatment(task5_output: Task5Output | None) -> str:
    """Extract the design system's callout treatment, with a safe fallback."""
    if task5_output is not None:
        for technique in task5_output.design_system.special_techniques:
            if technique.technique == "callout_treatment" and technique.visual_spec:
                return technique.visual_spec
    return DEFAULT_CALLOUT_TREATMENT


def build_text_elements(
    slide: SlideSpec,
    callout_treatment: str | None = None,
) -> str:
    """Build the text_elements section for a slide following Nano-Banana Pro format.

    Args:
        slide: The slide specification from Task 6.
        callout_treatment: The design system's visual treatment for callouts
            (``resolve_callout_treatment``). Falls back to a generic
            distinct treatment when None.

    Returns:
        Formatted text_elements string with text in quotes and placement info.
    """
    layout_pattern = slide.layout.pattern
    placement = LAYOUT_TEXT_PLACEMENT.get(
        layout_pattern, LAYOUT_TEXT_PLACEMENT["full_bleed"]
    )

    elements = []

    # Add headline
    if slide.content.headline:
        elements.append(
            f'HEADLINE: "{slide.content.headline}" - {placement["headline"]}'
        )

    # Add subheadline if present
    if slide.content.subheadline:
        elements.append(
            f'SUBHEADLINE: "{slide.content.subheadline}" - medium serif, below headline'
        )

    # Add body text if present
    if slide.content.body_text:
        elements.append(f'BODY: "{slide.content.body_text}" - {placement["body"]}')

    # Add quote if present
    if slide.content.quote:
        elements.append(f'QUOTE: "{slide.content.quote}" - italic serif, emphasized')

    # Add callout if present — baked into the image with the design system's
    # distinct callout treatment (previously omitted entirely).
    if slide.content.callout:
        treatment = callout_treatment or DEFAULT_CALLOUT_TREATMENT
        elements.append(f'CALLOUT: "{slide.content.callout}" - {treatment}')

    # Add labels if present
    if slide.content.labels:
        for label in slide.content.labels:
            elements.append(
                f'LABEL: "{label}" - small bold sans-serif, near relevant element'
            )

    return "\n".join(elements)


def assemble_full_prompt(sections: ImagePromptSections) -> str:
    """Assemble the final image prompt deterministically from its sections.

    The model writes each prompt once (as sections); this builds the
    ``full_prompt`` that image generation consumes, eliminating the
    near-verbatim duplication and transcription drift of having the LLM write
    both representations.
    """
    parts: list[str] = [
        f"GOAL: {sections.goal}",
        f"SUBJECT: {sections.subject}",
        f"COMPOSITION: {sections.composition}",
    ]
    if sections.spatial_relationships:
        parts.append(f"SPATIAL RELATIONSHIPS: {sections.spatial_relationships}")
    parts.append(f"SETTING: {sections.setting}")
    parts.append(f"LIGHTING: {sections.lighting}")
    if sections.text_elements:
        parts.append(f"TEXT ELEMENTS:\n{sections.text_elements}")
    parts.append(f"STYLE: {sections.style}")
    parts.append(f"FIDELITY: {sections.fidelity}")
    parts.append(f"CONSISTENCY: {sections.consistency}")
    return "\n\n".join(parts)


def finalize_draft(
    draft: ImagePromptDraft,
    slide: SlideSpec | None,
    visuals_only: bool,
    callout_treatment: str | None,
) -> ImagePrompt:
    """Turn an LLM draft into the final ImagePrompt.

    Injects the pre-computed text elements (code-authored, not model-echoed)
    and assembles ``full_prompt`` from the sections.
    """
    sections = draft.sections
    if visuals_only:
        sections.text_elements = None
    elif slide is not None:
        sections.text_elements = build_text_elements(slide, callout_treatment) or None
    return ImagePrompt(
        full_prompt=assemble_full_prompt(sections),
        sections=sections,
        generation_notes=draft.generation_notes,
    )


def format_character_canon(canon: list[CharacterSheet]) -> str:
    """Render the character canon block injected into the task7 LLM context."""
    lines = "\n".join(f"- {sheet.identity_lock_line()}" for sheet in canon)
    return f"""
## Character Canon (fiction — locked identities)

The following canonical character descriptions come from the source analysis
(task2). They are the single source of truth for how each character looks.

{lines}

Rules:
- Use these EXACT names in characters_in_frame (a parenthetical for position/
  state is fine, e.g. "Mina Harker (doorway, nervous)").
- Copy each character's description VERBATIM into the CONSISTENCY section of
  every slide where that character appears. Do not paraphrase, restyle, or
  re-invent faces, hair, builds, or costumes.
"""


def inject_character_locks(
    image_prompt: ImagePrompt,
    characters_in_frame: list[str] | None,
    canon: list[CharacterSheet],
) -> None:
    """Deterministically embed canonical descriptions into a slide prompt.

    For every canon character matched in ``characters_in_frame`` (entries may
    carry parentheticals like "Name (doorway)"), ensure the character's
    ``identity_lock_line()`` appears verbatim in ``full_prompt``. Lines the
    LLM already copied verbatim are not duplicated. No-op without matches,
    so non-fiction slides are untouched.
    """
    if not characters_in_frame or not canon:
        return

    def in_frame(name: str) -> bool:
        # Per-entry prefix match (case-insensitive): "Mina Harker (doorway)"
        # matches canon name "Mina Harker", but a name appearing only inside
        # another entry's parenthetical does not.
        return any(
            entry.strip().lower().startswith(name.lower())
            for entry in characters_in_frame
        )

    missing = [
        sheet.identity_lock_line()
        for sheet in canon
        if in_frame(sheet.name)
        and sheet.identity_lock_line() not in image_prompt.full_prompt
    ]
    if missing:
        lock_block = (
            "\n\nCHARACTER IDENTITY LOCK (canonical, identical on every slide):\n"
        )
        lock_block += "\n".join(f"- {line}" for line in missing)
        image_prompt.full_prompt += lock_block


def apply_character_canon(
    task7_output: Task7Output,
    task6_output: Task6Output,
    canon: list[CharacterSheet] | None,
) -> None:
    """Inject identity locks into all slide prompts based on task6 framing."""
    if not canon:
        return
    frames = {
        slide.number: slide.visual.image_spec.characters_in_frame
        for slide in task6_output.slides
    }
    for slide_prompt in task7_output.slide_prompts:
        inject_character_locks(
            slide_prompt.image_prompt,
            frames.get(slide_prompt.slide_number),
            canon,
        )


def run_task_07(
    task1_output: Task1Output,
    task5_output: Task5Output,
    task6_output: Task6Output,
    client: TextClient,
    model: str,
    visuals_only: bool = False,
    style_prompt: str | None = None,
    provider: str = "gemini",
    max_output_tokens: int | None = None,
    character_canon: list[CharacterSheet] | None = None,
) -> Task7Output:
    """Run Task 7: Image Prompt Generation.

    Transforms slide specifications into image prompts optimized for the
    target provider, following the Nano-Banana Pro methodology.

    Args:
        task1_output: Output from Task 1 (genre classification).
        task5_output: Output from Task 5 (design system).
        task6_output: Output from Task 6 (slide specifications).
        client: The Gemini client for text generation.
        model: The model to use for generation.
        visuals_only: If True, generate prompts without text elements.
        style_prompt: Optional style transfer prompt to customize visual style.
        provider: Target image generation provider (gemini, openai, xai).
        character_canon: Canonical character sheets from task2 (fiction only).
            Injected into the LLM context and enforced verbatim in post-
            processing on every slide where the character is in frame.

    Returns:
        Task7Output with image prompts for all slides.
    """
    # Load the task prompt template
    system_prompt = load_task_prompt(7)

    # Load provider-specific best practices
    provider_guidelines = load_provider_guidelines(provider)
    if provider_guidelines:
        system_prompt += (
            f"\n\n## Provider-Specific Guidelines ({provider})\n\n{provider_guidelines}"
        )

    # Format design system as YAML
    design_system_yaml = dump_yaml(task5_output.design_system)

    # Generate image prompts for all slides in a single call
    slides_yaml = dump_yaml([s.model_dump() for s in task6_output.slides])

    # Inject the canonical character sheets for fiction sources
    if character_canon:
        system_prompt += "\n\n" + format_character_canon(character_canon)

    # Get presentation title from first slide
    title = (
        task6_output.slides[0].content.headline if task6_output.slides else "Untitled"
    )
    total_slides = len(task6_output.slides)

    # Format the user prompt
    user_prompt = f"""Please generate image prompts for all slides in this presentation.

## Presentation Context

Genre: {task1_output.genre}
Title: {title}
Total slides: {total_slides}

## Design System (from Task 5)

{design_system_yaml}

## Slide Specifications (from Task 6)

{slides_yaml}

---

Generate image prompts for ALL slides in the structured format specified in the system instructions.
Follow the Nano-Banana Pro methodology and ensure visual consistency across the presentation.

IMPORTANT: Write each prompt ONCE, as sections only.
- Do NOT write a full_prompt — the pipeline assembles it from your sections
- Set text_elements to null — the pipeline injects the pre-computed text elements (headline, body, quote, callout) per slide
- Do NOT add text-related items to negative_prompts (no "text", "letters", "words", "typography")"""

    # Add visuals-only instructions if enabled
    if visuals_only:
        user_prompt += """

## VISUALS-ONLY MODE

IMPORTANT: Generate pure visual images with NO text elements.
- Do NOT include any text, headlines, subtitles, or labels in any section
- Do NOT specify text placement zones or typography in the image
- Add to negative_prompts: "text", "letters", "words", "typography", "captions", "labels"
- The images should be pure visuals suitable as backgrounds"""

    # Add custom style transfer instructions if provided
    if style_prompt:
        user_prompt += f"""

## Custom Style Transfer Instructions

IMPORTANT: Apply the following style guidelines to ALL generated image prompts.
These style instructions should OVERRIDE the default visual style from the design system.

{style_prompt}

---
When generating the STYLE section of each image prompt, prioritize these custom style
guidelines over the design system's visual_style settings.

## Style Identity (CONSISTENT across all slides)

These elements define the style and MUST remain identical on every slide:
- Medium/technique (if ink wash, ALL slides are ink wash — no digital rendering)
- Color palette (if B&W, ALL slides are B&W — no exceptions, no "accent colors")
- Texture/grain (if vintage grain, ALL slides have vintage grain — never "cinematic" or "sharp")
- Era feel (if 1920s, ALL slides are 1920s — never modern)
- Character rendering (if silent film style, ALL characters look silent film style)
- Forbidden elements in negative_prompts

Before generating EACH slide's prompt, re-read the style transfer above and include:
1. The SAME style descriptors in STYLE section
2. The SAME texture in FIDELITY section
3. The SAME forbidden elements in negative_prompts

DO NOT let "hero shots", "climax scenes", or "resolution slides" drift to modern aesthetics.

## Composition Variety (MUST CHANGE between slides)

While the style identity stays locked, the following MUST vary across slides to prevent
visual monotony. A presentation where every slide looks the same will bore the audience.

Vary per slide:
- **Subject matter**: Different primary subjects — don't repeat the same object or scene type
- **Scale and framing**: Rotate between close-up, medium shot, wide/establishing, overhead/plan view
- **Composition approach**: Alternate between object isolation, environmental scene, human gesture/action, and abstract/textural
- **Spatial depth**: Mix shallow (single object in space) with deep (layered foreground/midground/background)
- **Tonal dominance**: Alternate dark-dominant, light-dominant, and high-contrast slides

HARD RULE: No two consecutive slides may share BOTH the same primary subject type AND the same framing/scale. If slide 5 is a close-up of a ceramic object, slide 6 must differ in subject OR framing OR both."""

    # Generate structured output (high token limit for 13+ slides with detailed prompts)
    draft = client.generate_structured(
        prompt=user_prompt,
        response_schema=Task7Draft,
        model=model,
        system_instruction=system_prompt,
        max_output_tokens=max_output_tokens,
        task="task7",
    )

    # Assemble final prompts: inject pre-computed text elements and build
    # full_prompt deterministically from the model's sections.
    slides_by_number = {slide.number: slide for slide in task6_output.slides}
    callout_treatment = resolve_callout_treatment(task5_output)
    result = Task7Output(
        slide_prompts=[
            SlideImagePrompt(
                slide_number=draft_prompt.slide_number,
                image_prompt=finalize_draft(
                    draft_prompt.image_prompt,
                    slides_by_number.get(draft_prompt.slide_number),
                    visuals_only,
                    callout_treatment,
                ),
            )
            for draft_prompt in draft.slide_prompts
        ]
    )

    # Enforce verbatim identity locks regardless of how well the LLM copied.
    apply_character_canon(result, task6_output, character_canon)

    return result


def run_task_07_single_slide(
    slide_spec: dict,
    task1_output: Task1Output,
    task5_output: Task5Output,
    slide_number: int,
    total_slides: int,
    title: str,
    client: TextClient,
    model: str,
    visuals_only: bool = False,
    style_prompt: str | None = None,
    provider: str = "gemini",
    character_canon: list[CharacterSheet] | None = None,
) -> SlideImagePrompt:
    """Run Task 7 for a single slide (alternative approach for large presentations).

    Args:
        slide_spec: Single slide specification from Task 6.
        task1_output: Output from Task 1 (genre classification).
        task5_output: Output from Task 5 (design system).
        slide_number: Current slide number.
        total_slides: Total number of slides.
        title: Presentation title.
        client: The Gemini client for text generation.
        model: The model to use for generation.
        visuals_only: If True, generate prompts without text elements.
        style_prompt: Optional style transfer prompt to customize visual style.
        provider: Target image generation provider (gemini, openai, xai).
        character_canon: Canonical character sheets from task2 (fiction only).

    Returns:
        SlideImagePrompt with image prompt for the slide.
    """
    # Load the task prompt template
    system_prompt = load_task_prompt(7)

    # Load provider-specific best practices
    provider_guidelines = load_provider_guidelines(provider)
    if provider_guidelines:
        system_prompt += (
            f"\n\n## Provider-Specific Guidelines ({provider})\n\n{provider_guidelines}"
        )

    # Inject the canonical character sheets for fiction sources
    if character_canon:
        system_prompt += "\n\n" + format_character_canon(character_canon)

    # Format design system as YAML
    design_system_yaml = dump_yaml(task5_output.design_system)

    # Format slide spec as YAML
    slide_spec_yaml = dump_yaml(slide_spec)

    # Format the user prompt
    user_prompt = f"""Please generate an image prompt for the following slide.

## Presentation Context

Genre: {task1_output.genre}
Title: {title}
Slide number: {slide_number}
Total slides: {total_slides}

## Design System (from Task 5)

{design_system_yaml}

## Slide Specification (from Task 6)

{slide_spec_yaml}

---

Generate the image prompt in the structured format specified in the system instructions.
Follow the Nano-Banana Pro methodology.

IMPORTANT: Write the prompt ONCE, as sections only.
- Do NOT write a full_prompt — the pipeline assembles it from your sections
- Set text_elements to null — the pipeline injects the pre-computed text elements (headline, body, quote, callout) for this slide
- Do NOT add text-related items to negative_prompts"""

    # Add visuals-only instructions if enabled
    if visuals_only:
        user_prompt += """

## VISUALS-ONLY MODE

IMPORTANT: Generate pure visual image with NO text elements.
- Do NOT include any text, headlines, subtitles, or labels in any section
- Add to negative_prompts: "text", "letters", "words", "typography", "captions", "labels"
- The image should be a pure visual suitable as background"""

    # Add custom style transfer instructions if provided
    if style_prompt:
        user_prompt += f"""

## Custom Style Transfer Instructions

IMPORTANT: Apply the following style guidelines to this image prompt.
These style instructions should OVERRIDE the default visual style from the design system.

{style_prompt}

---
When generating the STYLE section of this image prompt, prioritize these custom style
guidelines over the design system's visual_style settings.

## Style Identity (CONSISTENT — slide {slide_number} of {total_slides})

This slide MUST have the EXACT SAME style identity as slide 1 and slide 2:
- Same medium/technique, color palette, texture/grain, era feel
- Same character rendering conventions
- Same forbidden elements in negative_prompts

DO NOT let this slide drift to modern aesthetics just because it's a later slide.

## Composition Variety (MUST DIFFER from adjacent slides)

While keeping style identity locked, this slide MUST be visually distinct from its neighbors:
- Use a DIFFERENT primary subject than the previous slide
- Use a DIFFERENT scale/framing (close-up vs medium vs wide vs overhead)
- Vary tonal dominance (dark vs light vs high-contrast) from adjacent slides"""

    # Generate structured output for single prompt
    draft = client.generate_structured(
        prompt=user_prompt,
        response_schema=ImagePromptDraft,
        model=model,
        system_instruction=system_prompt,
        task="task7",
    )

    # Inject pre-computed text elements and assemble full_prompt from sections.
    spec_model = SlideSpec.model_validate(slide_spec)
    result = finalize_draft(
        draft,
        spec_model,
        visuals_only,
        resolve_callout_treatment(task5_output),
    )

    # Enforce verbatim identity locks regardless of how well the LLM copied.
    if character_canon:
        inject_character_locks(
            result,
            spec_model.visual.image_spec.characters_in_frame,
            character_canon,
        )

    return SlideImagePrompt(slide_number=slide_number, image_prompt=result)
