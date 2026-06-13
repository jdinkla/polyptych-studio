"""Task I2: Image Prompt Generation for Infographic Pipeline."""

from ..client import TextClient
from ..models import TaskI0Output, TaskI1Output, TaskI2Output
from ..prompt_loader import load_infographic_task_prompt, load_provider_guidelines


def run_task_i2(
    source_essay: str,
    i0_output: TaskI0Output,
    i1_output: TaskI1Output,
    num_variants: int,
    client: TextClient,
    model: str,
    style_prompt: str | None = None,
    max_output_tokens: int | None = None,
    provider: str = "gemini",
    quality: str | None = None,
) -> TaskI2Output:
    """Run Task I2: Image Prompt Generation for Infographic.

    Generates N prompt variants, each a complete image generation prompt
    for a single-page infographic.

    Args:
        source_essay: The source text (for reference).
        i0_output: Output from Task I0 with content analysis.
        i1_output: Output from Task I1 with design specification.
        num_variants: Number of prompt variants to generate (1-5).
        client: The text client for generation.
        model: The model to use for generation.
        style_prompt: Optional style transfer prompt to apply.
        max_output_tokens: Optional max output token limit.
        provider: Image generation provider for best-practices guidelines.
        quality: Resolved rendering quality tier (e.g. "low", "medium",
            "high"), used to calibrate in-image text density.

    Returns:
        TaskI2Output with prompt variants.
    """
    system_prompt = load_infographic_task_prompt("i2")
    provider_guidelines = load_provider_guidelines(provider)
    if provider_guidelines:
        system_prompt += (
            f"\n\n## Provider-Specific Guidelines ({provider})\n\n{provider_guidelines}"
        )

    # Build I0 summary
    key_points_summary = "\n".join(
        f"- [{kp.id}] ({kp.importance}) {kp.statement}" for kp in i0_output.key_points
    )

    # Build I1 summary
    sections_summary = "\n".join(
        f"- {s.title} [{s.visual_element}] at {s.placement}: {s.visual_description}"
        for s in i1_output.sections
    )

    palette = i1_output.color_palette
    color_summary = (
        f"Primary: {palette.primary}, Secondary: {palette.secondary}, "
        f"Accent: {palette.accent}, Background: {palette.background}, "
        f"Text: {palette.text}"
    )

    style_section = ""
    if style_prompt:
        style_section = f"""
## Style Transfer

Apply the following visual style to all variants:

{style_prompt}
"""

    quality_section = ""
    if quality:
        quality_section = f"""
## Rendering Quality Tier

The image will be rendered at quality tier: **{quality}**. Calibrate the
amount and size of in-image text accordingly (see "Calibrating Text Density
to the Quality Tier" in the system instructions).
"""

    user_prompt = f"""Please generate {num_variants} infographic image prompt variant(s) based on the following analysis and design.

## Content Analysis (I0)

Title: {i0_output.title}
Subtitle: {i0_output.subtitle}
Thesis: {i0_output.thesis}

### Key Points
{key_points_summary}

## Design Specification (I1)

Layout: {i1_output.layout_type}
Orientation: {i1_output.orientation}
Visual Style: {i1_output.visual_style}
Icon Style: {i1_output.icon_style}
Title Treatment: {i1_output.title_treatment}
Flow: {i1_output.flow_description}
Typography: {i1_output.typography_notes}

### Sections
{sections_summary}

### Colors
{color_summary}
Rationale: {palette.rationale}
{style_section}{quality_section}
---

Generate exactly {num_variants} prompt variant(s), each a complete, self-contained image generation prompt.

Each variant should take a meaningfully different creative angle (different layout interpretation, visual metaphor, or emphasis) while faithfully representing the same content.

Output all variants in the structured format specified."""

    result = client.generate_structured(
        prompt=user_prompt,
        response_schema=TaskI2Output,
        model=model,
        system_instruction=system_prompt,
        max_output_tokens=max_output_tokens,
        task="i2",
    )

    return result
