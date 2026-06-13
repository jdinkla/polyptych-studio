"""Task 1: Genre Classification."""

from ..client import TextClient
from ..models import Task1Output
from ..prompt_loader import load_task_prompt


def run_task_01(
    source_essay: str,
    client: TextClient,
    model: str,
    mode_override: str | None = None,
) -> Task1Output:
    """Run Task 1: Genre Classification.

    Classifies the source essay into one of six genres and determines
    downstream slide generation parameters.

    Args:
        source_essay: The full markdown text of the source essay.
        client: The Gemini client for text generation.
        model: The model to use for generation.
        mode_override: If provided, forces the genre to this value instead of auto-detecting.
            Valid values: personal_essay, analytical_critique, policy_argument,
            fiction, strategic_diagnostic, conceptual_essay

    Returns:
        Task1Output with genre classification and parameters.
    """
    # Load the task prompt template
    system_prompt = load_task_prompt(1)

    # Format the user prompt with the source essay
    override_instruction = ""
    if mode_override and mode_override != "auto":
        override_instruction = f"""
## IMPORTANT: Genre Override

The user has explicitly specified that this content should be classified as **{mode_override}**.

You MUST:
1. Set the genre to "{mode_override}"
2. Use the corresponding parameters from the lookup table for this genre
3. Still analyze the signals present in the text (for documentation purposes)
4. Set confidence to 1.0 since this is a user-specified override

"""

    user_prompt = f"""Please analyze the following essay and classify its genre.
{override_instruction}
## Source Essay

{source_essay}

---

Provide your analysis in the structured format specified in the system instructions."""

    # Generate structured output
    result = client.generate_structured(
        prompt=user_prompt,
        response_schema=Task1Output,
        model=model,
        system_instruction=system_prompt,
        task="task1",
    )

    return result
