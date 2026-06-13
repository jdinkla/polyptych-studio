"""Task 3: Structure Planning."""

from ..client import TextClient
from ..models import Task1Output, Task2Output, Task3Output
from ..prompt_loader import load_task_prompt
from ..text_utils import dump_yaml


def run_task_03(
    task1_output: Task1Output,
    task2_output: Task2Output,
    client: TextClient,
    model: str,
) -> Task3Output:
    """Run Task 3: Structure Planning.

    Determines optimal slide count, sequence, and role assignments based on
    the source analysis and genre.

    Args:
        task1_output: Output from Task 1 (genre classification).
        task2_output: Output from Task 2 (source analysis).
        client: The Gemini client for text generation.
        model: The model to use for generation.

    Returns:
        Task3Output with structure planning results.
    """
    # Load the task prompt template
    system_prompt = load_task_prompt(3)

    # Format source analysis as YAML for the prompt
    source_analysis_yaml = dump_yaml(task2_output)

    # Format parameters from Task 1
    parameters_yaml = dump_yaml(
        {
            "compression_ratio": task1_output.parameters.compression_ratio,
            "structure_type": task1_output.parameters.structure_type,
            "metaphor_strategy": task1_output.parameters.metaphor_strategy,
        }
    )

    # Format concept architecture if available (conceptual_essay)
    concept_arch_section = ""
    if task2_output.concept_architecture:
        concept_arch_yaml = dump_yaml(task2_output.concept_architecture)
        concept_arch_section = f"""

## Concept Architecture (from Task 2)

{concept_arch_yaml}
"""

    # Format the user prompt
    user_prompt = f"""Please create a structure plan for the presentation based on the source analysis.

## Genre

{task1_output.genre}

## Parameters

{parameters_yaml}

## Source Analysis (from Task 2)

{source_analysis_yaml}
{concept_arch_section}
---

Provide your structure plan in the structured format specified in the system instructions.
Use the genre-specific arc template for "{task1_output.genre}"."""

    # Generate structured output
    result = client.generate_structured(
        prompt=user_prompt,
        response_schema=Task3Output,
        model=model,
        system_instruction=system_prompt,
        task="task3",
    )

    return result
