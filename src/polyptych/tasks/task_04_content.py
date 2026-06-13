"""Task 4: Content Allocation."""

from ..client import TextClient
from ..models import Task1Output, Task2Output, Task3Output, Task4Output
from ..prompt_loader import load_task_prompt
from ..text_utils import dump_yaml, number_paragraphs, parse_paragraphs


def run_task_04(
    source_essay: str,
    task1_output: Task1Output,
    task2_output: Task2Output,
    task3_output: Task3Output,
    client: TextClient,
    model: str,
) -> Task4Output:
    """Run Task 4: Content Allocation.

    Assigns specific source content to each slide, applying appropriate
    compression while preserving the essay's voice.

    Args:
        source_essay: The full markdown text of the source essay.
        task1_output: Output from Task 1 (genre classification).
        task2_output: Output from Task 2 (source analysis).
        task3_output: Output from Task 3 (structure planning).
        client: The Gemini client for text generation.
        model: The model to use for generation.

    Returns:
        Task4Output with content allocations for each slide.
    """
    # Load the task prompt template
    system_prompt = load_task_prompt(4)

    # Format slide sequence as YAML
    slide_sequence_yaml = dump_yaml(
        [s.model_dump() for s in task3_output.slide_sequence]
    )

    # Format source analysis as YAML (simplified for context)
    source_analysis_dict = {
        "structural_analysis": task2_output.structural_analysis.model_dump(),
        "quotable_passages": [q.model_dump() for q in task2_output.quotable_passages],
        "metaphor_inventory": task2_output.metaphor_inventory.model_dump(),
    }
    if task2_output.concept_architecture:
        source_analysis_dict["concept_architecture"] = (
            task2_output.concept_architecture.model_dump()
        )
    source_analysis_yaml = dump_yaml(source_analysis_dict)

    # Number paragraphs so the LLM can reference them by [N] ID
    numbered_essay = number_paragraphs(source_essay)

    # Format the user prompt
    user_prompt = f"""Please allocate content from the source essay to each slide.

## Source Essay

{numbered_essay}

## Compression Ratio

{task1_output.parameters.compression_ratio}

## Slide Sequence (from Task 3)

{slide_sequence_yaml}

## Source Analysis (from Task 2)

{source_analysis_yaml}

---

Provide content allocations in the structured format specified in the system instructions.
Apply the compression techniques appropriate for compression ratio {task1_output.parameters.compression_ratio}."""

    # Generate structured output
    result = client.generate_structured(
        prompt=user_prompt,
        response_schema=Task4Output,
        model=model,
        system_instruction=system_prompt,
        task="task4",
    )

    # Post-process: populate original_text_start and compression_applied
    # from the source paragraphs (the model cannot count words reliably and
    # used to fabricate the compression value).
    paragraphs = parse_paragraphs(source_essay)

    for alloc in result.allocations:
        if alloc.body_text and alloc.body_text.source_paragraphs:
            earliest = min(alloc.body_text.source_paragraphs)
            para_text = paragraphs.get(earliest)
            if para_text:
                alloc.body_text.original_text_start = para_text[:80]

            source_words = sum(
                len(paragraphs.get(p, "").split())
                for p in alloc.body_text.source_paragraphs
            )
            summary_words = len(alloc.body_text.summary.split())
            alloc.body_text.compression_applied = (
                round(source_words / summary_words, 2)
                if source_words and summary_words
                else None
            )

    return result
