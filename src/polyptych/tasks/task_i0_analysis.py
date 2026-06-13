"""Task I0: Content Analysis for Infographic Pipeline."""

from ..client import TextClient
from ..models import TaskI0Output
from ..prompt_loader import load_infographic_task_prompt
from ..text_utils import number_paragraphs


def run_task_i0(
    source_essay: str,
    client: TextClient,
    model: str,
    max_output_tokens: int | None = None,
) -> TaskI0Output:
    """Run Task I0: Content Analysis for Infographic.

    Analyzes source content to extract key points, relationships,
    visualizable data, and structural patterns for infographic design.

    Args:
        source_essay: The source text to analyze.
        client: The text client for generation.
        model: The model to use for generation.
        max_output_tokens: Optional max output token limit.

    Returns:
        TaskI0Output with content analysis results.
    """
    system_prompt = load_infographic_task_prompt("i0")
    numbered_essay = number_paragraphs(source_essay)

    user_prompt = f"""Please analyze the following source text for infographic generation.

## Source Text

{numbered_essay}

---

Analyze this content following the methodology in the system instructions:

1. Identify the core message, title, and subtitle
2. Extract 5-12 key points with importance levels
3. Map relationships between key points
4. Identify data elements suitable for visualization
5. Determine the primary content structure pattern
6. Recommend 3-6 major sections

Output the complete analysis in the structured format specified."""

    result = client.generate_structured(
        prompt=user_prompt,
        response_schema=TaskI0Output,
        model=model,
        system_instruction=system_prompt,
        max_output_tokens=max_output_tokens,
        task="i0",
    )

    return result
