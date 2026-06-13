"""Task 6: Slide Specification."""

from ..client import TextClient
from ..models import (
    Task1Output,
    Task2Output,
    Task3Output,
    Task4Output,
    Task5Output,
    Task6Output,
)
from ..prompt_loader import load_task_prompt
from ..text_utils import dump_yaml


def run_task_06(
    task1_output: Task1Output,
    task2_output: Task2Output,
    task3_output: Task3Output,
    task4_output: Task4Output,
    task5_output: Task5Output,
    client: TextClient,
    model: str,
) -> Task6Output:
    """Run Task 6: Slide Specification.

    Generates complete, production-ready specifications for each slide.

    Args:
        task1_output: Output from Task 1 (genre classification).
        task2_output: Output from Task 2 (source analysis).
        task3_output: Output from Task 3 (structure planning).
        task4_output: Output from Task 4 (content allocation).
        task5_output: Output from Task 5 (design system).
        client: The Gemini client for text generation.
        model: The model to use for generation.

    Returns:
        Task6Output with complete slide specifications.
    """
    # Load the task prompt template (genre-specific if available)
    system_prompt = load_task_prompt(6, genre=task1_output.genre)

    # Format content allocation as YAML
    content_allocation_yaml = dump_yaml(
        [a.model_dump() for a in task4_output.allocations]
    )

    # Format design system as YAML
    design_system_yaml = dump_yaml(task5_output.design_system)

    # Format slide sequence as YAML
    slide_sequence_yaml = dump_yaml(
        [s.model_dump() for s in task3_output.slide_sequence]
    )

    # Format source analysis as YAML (simplified)
    source_analysis: dict[str, object] = {
        "metaphor_inventory": task2_output.metaphor_inventory.model_dump(),
        "emotional_arc": task2_output.emotional_arc.model_dump(),
    }
    # Fiction: expose the canonical character sheets so characters_in_frame
    # uses the exact canonical names (task7 matches identity locks on them).
    if task2_output.character_canon:
        source_analysis["character_canon"] = [
            sheet.model_dump() for sheet in task2_output.character_canon
        ]
    source_analysis_yaml = dump_yaml(source_analysis)

    # Format the user prompt
    user_prompt = f"""Please generate complete slide specifications for each slide.

## Content Allocation (from Task 4)

{content_allocation_yaml}

## Design System (from Task 5)

{design_system_yaml}

## Slide Sequence (from Task 3)

{slide_sequence_yaml}

## Source Analysis (from Task 2)

{source_analysis_yaml}

---

Provide complete slide specifications in the structured format specified in the system instructions.
Ensure each slide has all required fields filled in according to the design system."""

    # Generate structured output
    result = client.generate_structured(
        prompt=user_prompt,
        response_schema=Task6Output,
        model=model,
        system_instruction=system_prompt,
        task="task6",
    )

    return result
