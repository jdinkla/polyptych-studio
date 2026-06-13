"""Task I1: Design Specification for Infographic Pipeline."""

from ..client import TextClient
from ..models import TaskI0Output, TaskI1Output
from ..prompt_loader import load_infographic_task_prompt


def run_task_i1(
    source_essay: str,
    i0_output: TaskI0Output,
    client: TextClient,
    model: str,
    style_prompt: str | None = None,
    max_output_tokens: int | None = None,
) -> TaskI1Output:
    """Run Task I1: Design Specification for Infographic.

    Translates the content analysis into a concrete visual design
    specification including layout, sections, colors, and style.

    Args:
        source_essay: The source text (for reference).
        i0_output: Output from Task I0 with content analysis.
        client: The text client for generation.
        model: The model to use for generation.
        style_prompt: Optional style transfer preset the final image will be
            rendered with; the design should align with it.
        max_output_tokens: Optional max output token limit.

    Returns:
        TaskI1Output with design specification.
    """
    system_prompt = load_infographic_task_prompt("i1")

    # Build I0 context summary
    key_points_summary = "\n".join(
        f"- [{kp.id}] ({kp.importance}) {kp.statement}" for kp in i0_output.key_points
    )

    relationships_summary = "\n".join(
        f"- {r.from_point} --{r.relationship_type}--> {r.to_point}: {r.label}"
        for r in i0_output.relationships
    )

    visualizable_summary = "\n".join(
        f"- {v.data_type}: {v.description} (values: {', '.join(v.values)})"
        for v in i0_output.visualizable_data
    )

    style_section = ""
    if style_prompt:
        style_section = f"""
## Style Transfer Preset

The final image will be rendered with the style transfer preset below. Align
your design with it: pick the `visual_style` value closest to the preset's
aesthetic, and derive the color palette from the preset's stated colors
instead of inventing a conflicting one.

{style_prompt}
"""

    user_prompt = f"""Please create an infographic design specification based on the following content analysis.

## Content Analysis (I0)

### Title & Message
Title: {i0_output.title}
Subtitle: {i0_output.subtitle}
Thesis: {i0_output.thesis}
Tone: {i0_output.tone}
Target Audience: {i0_output.target_audience}

### Content Structure
Pattern: {i0_output.content_structure.primary_pattern}
Rationale: {i0_output.content_structure.rationale}
Recommended Sections: {i0_output.content_structure.section_count}

### Key Points
{key_points_summary}

### Relationships
{relationships_summary}

### Visualizable Data
{visualizable_summary}
{style_section}
---

Design the infographic following the methodology in the system instructions:

1. Choose the best layout type for this content structure
2. Design {i0_output.content_structure.section_count} sections with appropriate visual elements
3. Select a color palette that suits the tone and audience
4. Choose a visual and icon style
5. Describe the title treatment and reading flow

Output the complete design specification in the structured format specified."""

    result = client.generate_structured(
        prompt=user_prompt,
        response_schema=TaskI1Output,
        model=model,
        system_instruction=system_prompt,
        max_output_tokens=max_output_tokens,
        task="i1",
    )

    return result
