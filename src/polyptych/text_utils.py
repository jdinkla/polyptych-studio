"""Text preprocessing utilities for slide generation."""

from __future__ import annotations

import re

import yaml
from pydantic import BaseModel


def dump_yaml(data: BaseModel | dict | list) -> str:
    """Serialize data to YAML with standard pipeline parameters.

    Accepts a Pydantic BaseModel (auto-calls model_dump()), dict, or list.
    """
    if isinstance(data, BaseModel):
        data = data.model_dump()
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)


def number_paragraphs(source_text: str) -> str:
    """Prepend [N] IDs to each paragraph in the source text.

    Uses the same splitting logic as parse_paragraphs() (split on blank lines,
    1-indexed) so the LLM can reference paragraph numbers without having to
    count them itself.

    Args:
        source_text: The raw source essay text.

    Returns:
        The text with [N] prefixed to each paragraph.
    """
    blocks = re.split(r"\n\s*\n", source_text.strip())
    numbered_blocks = []
    for i, block in enumerate(blocks, start=1):
        text = block.strip()
        if text:
            numbered_blocks.append(f"[{i}] {text}")
    return "\n\n".join(numbered_blocks)


def extract_avoid_rules(style_prompt: str) -> list[str]:
    """Parse the **Avoid** section from a style preset markdown string.

    Looks for a bold "Avoid" header followed by bullet lines (using * or -
    markers). Returns each bullet as a stripped string, preserving wording.

    Returns an empty list when no Avoid section is found.
    """
    match = re.search(
        r"\*\*Avoid\*\*\s*\n(.*?)(?=\n\*\*|\n##|\Z)",
        style_prompt,
        re.DOTALL,
    )
    if not match:
        return []
    section = match.group(1)
    rules: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped and stripped[0] in ("*", "-"):
            rule = stripped.lstrip("*- ").strip()
            if rule:
                rules.append(rule)
    return rules


_STOP_WORDS = frozenset(
    {
        # English function words
        "a",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "do",
        "for",
        "from",
        "had",
        "has",
        "have",
        "if",
        "in",
        "is",
        "it",
        "its",
        "not",
        "of",
        "on",
        "or",
        "so",
        "the",
        "to",
        "too",
        "was",
        "with",
        "no",
        "nor",
        "this",
        "that",
        "must",
        "should",
        # Generic terms that cause false positives against technique/style names
        "anime",
        "elements",
        "effects",
        "designs",
        "scenes",
        "poses",
        "expressions",
        "reactions",
        "aesthetics",
        "tropes",
        "style",
        "look",
        "dramatic",
        "dynamic",
        "heavy",
        "overly",
        "bright",
        "modern",
        "character",
        "rendering",
        "palettes",
        "color",
        "clothing",
    }
)


def derive_avoid_keywords(avoid_rules: list[str]) -> set[str]:
    """Extract lowercase keywords from avoid rules for substring matching.

    Tokenizes each rule on commas, "or", and whitespace, then filters out
    stop words and tokens shorter than 4 characters. Returns a set of
    keywords suitable for substring checks against technique names and
    free-text fields.
    """
    keywords: set[str] = set()
    for rule in avoid_rules:
        # Split on commas and " or " first, then whitespace-tokenize each part
        parts = re.split(r",|\bor\b", rule.lower())
        for part in parts:
            tokens = part.split()
            for token in tokens:
                # Strip non-alpha characters from edges
                clean = re.sub(r"^[^a-z]+|[^a-z]+$", "", token)
                if clean and len(clean) >= 4 and clean not in _STOP_WORDS:
                    keywords.add(clean)
    return keywords


def extract_allowed_rendering_techniques(style_prompt: str) -> list[str] | None:
    """Parse the **Allowed Rendering Techniques** section from a style preset.

    Looks for a bold "Allowed Rendering Techniques" header followed by bullet
    lines (using * or - markers). Returns each bullet as a stripped string.

    Returns None when no section is found (= all rendering techniques allowed).
    """
    match = re.search(
        r"\*\*Allowed Rendering Techniques\*\*\s*\n(.*?)(?=\n\*\*|\n##|\Z)",
        style_prompt,
        re.DOTALL,
    )
    if not match:
        return None
    section = match.group(1)
    techniques: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped and stripped[0] in ("*", "-"):
            technique = stripped.lstrip("*- ").strip().strip("`")
            if technique:
                techniques.append(technique)
    return techniques


def parse_paragraphs(source_text: str) -> dict[int, str]:
    """Parse source text into a dict mapping paragraph numbers to their text.

    Uses the same splitting logic as number_paragraphs() so paragraph IDs
    are consistent across the pipeline.

    Args:
        source_text: The raw source essay text.

    Returns:
        A dict mapping 1-indexed paragraph numbers to paragraph text.
    """
    blocks = re.split(r"\n\s*\n", source_text.strip())
    return {
        i: block.strip() for i, block in enumerate(blocks, start=1) if block.strip()
    }
