"""Task 5: Visual Design Specification."""

from ..client import TextClient
from ..models import Task1Output, Task2Output, Task4Output, Task5Output
from ..prompt_loader import load_task_prompt
from ..text_utils import dump_yaml


def run_task_05(
    task1_output: Task1Output,
    task2_output: Task2Output,
    task4_output: Task4Output,
    client: TextClient,
    model: str,
    style_prompt: str | None = None,
) -> Task5Output:
    """Run Task 5: Visual Design Specification.

    Establishes the visual design system for the presentation based on genre,
    content, and metaphor inventory.

    Args:
        task1_output: Output from Task 1 (genre classification).
        task2_output: Output from Task 2 (source analysis).
        task4_output: Output from Task 4 (content allocation).
        client: The Gemini client for text generation.
        model: The model to use for generation.
        style_prompt: Optional style transfer preset the final images will be
            rendered with; the design system should align with it.

    Returns:
        Task5Output with design system specification.
    """
    # Load the task prompt template
    system_prompt = load_task_prompt(5)

    # Format content allocation as YAML (simplified)
    content_allocation_yaml = dump_yaml(
        [a.model_dump() for a in task4_output.allocations]
    )

    # Format metaphor inventory as YAML
    metaphor_inventory_yaml = dump_yaml(task2_output.metaphor_inventory)

    # Format parameters
    parameters_yaml = dump_yaml(
        {
            "color_system": task1_output.parameters.color_system,
            "metaphor_strategy": task1_output.parameters.metaphor_strategy,
        }
    )

    style_section = ""
    if style_prompt:
        style_section = f"""
## Style Transfer Preset

The final images will be rendered with the style transfer preset below. Align
your design system with it: derive the color palette and background from the
preset's stated colors, pick a `visual_style.primary` close to the preset's
aesthetic, and keep the motif compatible — the prompt generation step applies
that preset to every image, and a conflicting design here produces
contradictory directives downstream.

{style_prompt}
"""

    # Format the user prompt
    user_prompt = f"""Please create a visual design system for this presentation.

## Genre

{task1_output.genre}

## Parameters

{parameters_yaml}

## Metaphor Inventory (from Task 2)

{metaphor_inventory_yaml}

## Content Allocation (from Task 4)

{content_allocation_yaml}
{style_section}
---

Provide the design system in the structured format specified in the system instructions.
Apply the design rules appropriate for the "{task1_output.genre}" genre."""

    # Generate structured output
    result = client.generate_structured(
        prompt=user_prompt,
        response_schema=Task5Output,
        model=model,
        system_instruction=system_prompt,
        task="task5",
    )

    return result
