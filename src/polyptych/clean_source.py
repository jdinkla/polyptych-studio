"""Clean PDF-to-markdown conversion artifacts from source files.

Removes page numbers, footnote blocks, footnote superscripts, TOC with dot leaders,
broken image references, and unnecessary backslash escaping.
"""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CleaningConfig:
    """Configuration for which cleaning passes to enable."""

    remove_toc: bool = True
    remove_image_refs: bool = True
    remove_footnotes: bool = True  # strips both blocks and superscripts
    remove_page_numbers: bool = True
    unescape_chars: bool = True


@dataclass
class CleaningResult:
    """Statistics from a cleaning run."""

    original_lines: int = 0
    cleaned_lines: int = 0
    toc_lines_removed: int = 0
    image_refs_removed: int = 0
    footnote_refs_removed: int = 0  # superscripts stripped
    footnote_blocks_removed: int = 0  # block lines stripped
    page_numbers_removed: int = 0
    escapes_fixed: int = 0


def remove_toc(text: str) -> tuple[str, int]:
    """Remove table of contents with dot-leader lines.

    Finds a CONTENTS heading, then removes all lines until the first chapter
    heading that is NOT followed by dot leaders.
    """
    lines = text.split("\n")
    # Find the CONTENTS heading
    contents_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^\*{0,2}CONTENTS\*{0,2}\s*$", line.strip()):
            contents_idx = i
            break

    if contents_idx is None:
        return text, 0

    # Find the end of TOC: first chapter heading pattern not part of TOC
    # Chapter headings look like **1. or **1\. at the start
    # TOC lines contain 5+ consecutive dots
    toc_end = None
    for i in range(contents_idx + 1, len(lines)):
        line = lines[i].strip()
        # A chapter heading that starts the actual content (not a TOC entry)
        if re.match(r"\*{2}\d+\\?\.", line) and "....." not in line:
            toc_end = i
            break

    if toc_end is None:
        # No chapter heading found after TOC; remove to end of consecutive TOC-like lines
        toc_end = contents_idx + 1
        for i in range(contents_idx + 1, len(lines)):
            line = lines[i].strip()
            if (
                line == ""
                or "....." in line
                or re.match(r"^\*", line)
                or re.match(r"^[A-Z]", line)
            ):
                toc_end = i + 1
            else:
                break

    removed = toc_end - contents_idx
    result_lines = lines[:contents_idx] + lines[toc_end:]
    return "\n".join(result_lines), removed


def remove_image_refs(text: str) -> tuple[str, int]:
    """Remove broken image references and their captions.

    Matches lines like *![][imageN]* and the immediately following caption line.
    """
    lines = text.split("\n")
    result = []
    count = 0
    skip_next = False

    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
        if re.match(r"^\s*\*?!\[\]\[image\d+\]\*?\s*$", line.strip()):
            count += 1
            # Skip the following caption line if it's a short non-heading, non-blank line
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if (
                    next_line
                    and not next_line.startswith("**")
                    and len(next_line) < 200
                ):
                    skip_next = True
            continue
        result.append(line)

    return "\n".join(result), count


def remove_footnote_blocks(text: str) -> tuple[str, int]:
    """Remove footnote reference blocks.

    Footnote blocks start with a line of whitespace (typically `    ` or blank),
    followed by lines starting with a number + space (e.g., `1 General C.C. Krulak...`).
    """
    lines = text.split("\n")
    result = []
    count = 0
    i = 0

    while i < len(lines):
        # Check for separator line (whitespace-only, often `    `) followed by footnote
        if re.match(r"^[\s]*$", lines[i]):
            # Look ahead for footnote lines
            j = i + 1
            # Skip additional blank lines
            while j < len(lines) and re.match(r"^\s*$", lines[j]):
                j += 1
            # Check if next non-blank line starts a footnote (number + space at start)
            if j < len(lines) and re.match(r"^\d{1,3}\s+\S", lines[j]):
                # This is a footnote block - consume all footnote lines
                block_start = i
                # Consume the separator lines
                while j < len(lines):
                    line = lines[j].strip()
                    if line == "":
                        # Blank line - check if followed by another footnote
                        k = j + 1
                        while k < len(lines) and re.match(r"^\s*$", lines[k]):
                            k += 1
                        if k < len(lines) and re.match(r"^\d{1,3}\s+\S", lines[k]):
                            j = k + 1
                            continue
                        else:
                            break
                    elif re.match(r"^\d{1,3}\s+\S", line):
                        j += 1
                        continue
                    else:
                        # Continuation line of a footnote (wrapped text)
                        # Check if it looks like content (starts with capital, no footnote number)
                        # Heuristic: if the previous line was a footnote, this could be continuation
                        if j > 0 and (
                            re.match(r"^\d{1,3}\s+\S", lines[j - 1].strip())
                            or lines[j - 1].strip() == ""
                        ):
                            j += 1
                            continue
                        else:
                            break

                removed_lines = j - block_start
                count += removed_lines
                i = j
                continue

        result.append(lines[i])
        i += 1

    return "\n".join(result), count


def remove_footnote_superscripts(text: str) -> tuple[str, int]:
    """Strip footnote superscript digits glued to word endings.

    Handles: `intellect1.` → `intellect.`, `war2.` → `war.`
    Does NOT strip: dates like 1997, model numbers like F-16, standalone numbers.
    """
    # Match 1-3 digits after a letter, before punctuation or whitespace/end
    # Negative lookbehind: don't match after digits (avoids stripping from years/numbers)
    # Negative lookbehind: don't match after hyphen (avoids F-16 → F-)
    pattern = r"(?<=[a-zA-Z])(\d{1,3})(?=[.,;:!?\s\)\]\"\'»]|$)"

    count = 0

    def _replace(m: re.Match) -> str:
        nonlocal count
        count += 1
        return ""

    result = re.sub(pattern, _replace, text)
    return result, count


def remove_page_numbers(text: str) -> tuple[str, int]:
    r"""Remove standalone page number lines.

    Removes lines matching `^\d{1,3}\s*$` (Arabic) or `^[ivxlc]+\s*$` (Roman)
    that are surrounded by blank lines.
    """
    lines = text.split("\n")
    result = []
    count = 0

    # Find first chapter heading to determine front matter boundary for Roman numerals
    first_chapter = len(lines)
    for i, line in enumerate(lines):
        if re.match(r"\*{2}\d+\\?\.", line.strip()):
            first_chapter = i
            break

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check for Arabic page numbers
        is_arabic = bool(re.match(r"^\d{1,3}$", stripped))

        # Check for Roman numeral page numbers (only in front matter)
        is_roman = bool(re.match(r"^[ivxlc]+$", stripped)) and i < first_chapter

        if (is_arabic or is_roman) and _is_surrounded_by_blanks(lines, i):
            count += 1
            continue

        result.append(line)

    return "\n".join(result), count


def _is_surrounded_by_blanks(lines: list[str], idx: int) -> bool:
    """Check if a line is surrounded by blank (or near-blank) lines."""
    prev_blank = idx == 0 or lines[idx - 1].strip() == ""
    next_blank = idx == len(lines) - 1 or lines[idx + 1].strip() == ""
    return prev_blank and next_blank


def unescape_chars(text: str) -> tuple[str, int]:
    r"""Remove unnecessary backslash escaping from PDF conversion.

    Cleans: `\.` → `.`, `\-` → `-`, `\+` → `+`, `\[` → `[`, `\]` → `]`,
    `\(` → `(`, `\)` → `)`.
    """
    chars = r".\-+[]()"
    count = 0
    for ch in chars:
        escaped = "\\" + ch
        occurrences = text.count(escaped)
        if occurrences > 0:
            count += occurrences
            text = text.replace(escaped, ch)
    return text, count


def normalize_whitespace(text: str) -> str:
    """Collapse 3+ consecutive blank lines to 2. Strip trailing whitespace per line."""
    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    # Collapse 3+ consecutive blank lines to 2
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text


def clean_source(
    text: str, config: CleaningConfig | None = None
) -> tuple[str, CleaningResult]:
    """Run all enabled cleaning passes in order. Idempotent."""
    if config is None:
        config = CleaningConfig()

    result = CleaningResult()
    result.original_lines = len(text.split("\n"))

    if config.remove_toc:
        text, result.toc_lines_removed = remove_toc(text)

    if config.remove_image_refs:
        text, result.image_refs_removed = remove_image_refs(text)

    if config.remove_footnotes:
        text, result.footnote_blocks_removed = remove_footnote_blocks(text)
        text, result.footnote_refs_removed = remove_footnote_superscripts(text)

    if config.remove_page_numbers:
        text, result.page_numbers_removed = remove_page_numbers(text)

    if config.unescape_chars:
        text, result.escapes_fixed = unescape_chars(text)

    text = normalize_whitespace(text)
    result.cleaned_lines = len(text.split("\n"))

    return text, result


def clean_file(
    input_path: Path,
    output_path: Path | None = None,
    config: CleaningConfig | None = None,
) -> tuple[Path, CleaningResult]:
    """Read file, clean, write output. Default output: <stem>-clean.md in same directory."""
    text = input_path.read_text(encoding="utf-8")

    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}-clean{input_path.suffix}"

    cleaned_text, result = clean_source(text, config)
    output_path.write_text(cleaned_text, encoding="utf-8")

    return output_path, result
