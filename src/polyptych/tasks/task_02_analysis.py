"""Task 2: Source Analysis."""

from ..client import TextClient
from ..models import Task1Output, Task2Output
from ..prompt_loader import load_task_prompt
from ..text_utils import number_paragraphs, parse_paragraphs


def run_task_02(
    source_essay: str,
    task1_output: Task1Output,
    client: TextClient,
    model: str,
) -> Task2Output:
    """Run Task 2: Source Analysis.

    Extracts raw materials from the source essay including structural elements,
    quotable passages, metaphors, and emotional arc.

    Args:
        source_essay: The full markdown text of the source essay.
        task1_output: Output from Task 1 (genre classification).
        client: The Gemini client for text generation.
        model: The model to use for generation.

    Returns:
        Task2Output with source analysis results.
    """
    # Load the task prompt template
    system_prompt = load_task_prompt(2)

    # Number paragraphs so the LLM can reference them by [N] ID
    # instead of having to count them itself (which fails on long texts)
    numbered_essay = number_paragraphs(source_essay)

    # Format the user prompt with the numbered source essay and genre
    user_prompt = f"""Please analyze the following essay and extract raw materials for slide generation.

## Source Essay

{numbered_essay}

## Genre Classification (from Task 1)

Genre: {task1_output.genre}

---

Provide your analysis in the structured format specified in the system instructions.
Apply the extraction guidelines appropriate for the "{task1_output.genre}" genre."""

    # Generate structured output
    result = client.generate_structured(
        prompt=user_prompt,
        response_schema=Task2Output,
        model=model,
        system_instruction=system_prompt,
        task="task2",
    )

    # Post-process: compute section word counts from the actual source text.
    # The model cannot count words and used to fabricate this value.
    paragraphs = parse_paragraphs(source_essay)
    for section in result.structural_analysis.sections:
        section.word_count = sum(
            len(paragraphs.get(p, "").split()) for p in section.paragraphs
        )

    return result
