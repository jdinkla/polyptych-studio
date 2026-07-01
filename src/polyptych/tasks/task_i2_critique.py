"""Task I2 Critique & Refine: Infographic prompt audit and correction."""

from ..client import TextClient
from ..models import TaskI0Output, TaskI1Output, TaskI2Critique, TaskI2Output
from ..prompt_loader import load_infographic_task_prompt, load_provider_guidelines
from ..text_utils import dump_yaml
from .task_i2_prompts import fold_variant_negatives


def _needs_refinement(critique: TaskI2Critique) -> bool:
    """Check if the critique warrants refinement."""
    return any(
        pi.severity in ("critical", "important") for pi in critique.prompt_issues
    )


def _context_sections(style_prompt: str | None, quality: str | None) -> str:
    """Optional style/quality context blocks shared by critique and refine."""
    sections = ""
    if style_prompt:
        sections += f"""
## Style Transfer Preset

The image will be rendered with this style preset:

{style_prompt}
"""
    if quality:
        sections += f"""
## Rendering Quality Tier

The image will be rendered at quality tier: **{quality}**.
"""
    return sections


def run_task_i2_critique(
    i0_output: TaskI0Output,
    i1_output: TaskI1Output,
    i2_output: TaskI2Output,
    client: TextClient,
    model: str,
    style_prompt: str | None = None,
    quality: str | None = None,
    max_output_tokens: int | None = None,
) -> TaskI2Critique:
    """Run I2 Critique: audit infographic prompts against I0/I1 upstream.

    Checks entity/color consistency, trim-induced semantic loss, key-content
    coverage, flow/spatial claims, text density vs. quality tier, style
    fidelity, and specificity — before the expensive image-generation step.

    Args:
        i0_output: Output from Task I0 with content analysis.
        i1_output: Output from Task I1 with design specification.
        i2_output: Output from Task I2 with prompt variants.
        client: The text generation client.
        model: The model to use for generation.
        style_prompt: Optional style transfer preset applied to the image.
        quality: Resolved rendering quality tier (calibrates text density).
        max_output_tokens: Optional output token limit.

    Returns:
        TaskI2Critique with per-variant issues and dropped-content listing.
    """
    system_prompt = load_infographic_task_prompt("i2_critique")
    i0_yaml = dump_yaml(i0_output)
    i1_yaml = dump_yaml(i1_output)
    i2_yaml = dump_yaml(i2_output)

    user_prompt = f"""Please audit the following infographic image prompts.

## I0 Content Analysis

```yaml
{i0_yaml}```

---

## I1 Design Specification

```yaml
{i1_yaml}```

---

## I2 Image Prompts

```yaml
{i2_yaml}```
{_context_sections(style_prompt, quality)}
---

Perform the audit described in the system instructions:

1. Entity & color consistency — same entity, same treatment everywhere
2. Trim-induced semantic loss — surviving elements must still carry their meaning
3. Key-content coverage — primary key points and strongest data must survive
4. Flow & spatial claims — every I1 flow relationship written into the prompt
5. Text density vs. quality tier
6. Style fidelity to the preset
7. Specificity — concrete enough to render, not overloaded

Audit each variant independently; differences between variants are intentional.

Provide your critique in the structured format specified."""

    return client.generate_structured(
        prompt=user_prompt,
        response_schema=TaskI2Critique,
        model=model,
        system_instruction=system_prompt,
        max_output_tokens=max_output_tokens,
        task="i2_critique",
    )


def run_task_i2_refine(
    i0_output: TaskI0Output,
    i1_output: TaskI1Output,
    i2_output: TaskI2Output,
    critique: TaskI2Critique,
    client: TextClient,
    model: str,
    style_prompt: str | None = None,
    quality: str | None = None,
    provider: str = "gemini",
    max_output_tokens: int | None = None,
) -> TaskI2Output:
    """Run I2 Refine: correct infographic prompts based on critique findings.

    Produces a full replacement TaskI2Output that fixes flagged issues while
    preserving unflagged variants and sections.

    Args:
        i0_output: Output from Task I0 with content analysis.
        i1_output: Output from Task I1 with design specification.
        i2_output: The current prompt variants to correct.
        critique: The critique identifying issues.
        client: The text generation client.
        model: The model to use for generation.
        style_prompt: Optional style transfer preset applied to the image.
        quality: Resolved rendering quality tier (text-density budget).
        provider: Image generation provider for best-practices guidelines.
        max_output_tokens: Optional output token limit.

    Returns:
        Revised TaskI2Output that addresses the critique findings.
    """
    system_prompt = load_infographic_task_prompt("i2_refine")
    provider_guidelines = load_provider_guidelines(provider)
    if provider_guidelines:
        system_prompt += (
            f"\n\n## Provider-Specific Guidelines ({provider})\n\n{provider_guidelines}"
        )

    i0_yaml = dump_yaml(i0_output)
    i1_yaml = dump_yaml(i1_output)
    i2_yaml = dump_yaml(i2_output)
    critique_yaml = dump_yaml(critique)

    user_prompt = f"""Please correct the following infographic image prompts based on the critique.

## I0 Content Analysis

```yaml
{i0_yaml}```

---

## I1 Design Specification

```yaml
{i1_yaml}```

---

## Current I2 Image Prompts

```yaml
{i2_yaml}```

---

## Critique Findings

```yaml
{critique_yaml}```
{_context_sections(style_prompt, quality)}
---

Revise the prompts following the system instructions:

1. Fix every flagged issue by its issue_type
2. Respect the quality tier's text-density budget (swap, don't just add)
3. Preserve unflagged variants and sections exactly
4. Keep the same variant count and variant_number values

Provide the complete corrected output in the structured format specified."""

    result = client.generate_structured(
        prompt=user_prompt,
        response_schema=TaskI2Output,
        model=model,
        system_instruction=system_prompt,
        max_output_tokens=max_output_tokens,
        task="i2_refine",
    )
    return fold_variant_negatives(result)
