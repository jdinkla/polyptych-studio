"""Cross-task referential integrity checks for ``polyptych validate``.

Schema validation checks each task YAML in isolation; the errors that actually
occur in practice — especially in local-skill mode where an agent writes the
YAML — span tasks: dangling scene-beat references, slide-count mismatches
between task3/task4/task6/task7, paragraph citations beyond the source's
length. This module adds a per-pipeline cross-task pass that runs after schema
validation whenever at least two task files are present.

Hard referential breaks are ``error`` (non-zero exit); soft content rules
(headline/quote word limits) are ``warning``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

import yaml
from pydantic import BaseModel

from .models import (
    Task2Output,
    Task3Output,
    Task4Output,
    Task6Output,
    Task7Output,
)
from .pipeline_config import TASK_OUTPUT_FILES
from .text_utils import parse_paragraphs

# Soft content rules, from the task prompts: headlines max 8 words (task-04
# and task-06, aligned in TASK-86), quotes under 25 words (task-04).
HEADLINE_MAX_WORDS = 8
QUOTE_MAX_WORDS = 25


@dataclass
class Finding:
    """A single cross-task validation finding."""

    severity: Literal["error", "warning"]
    check: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "check": self.check,
            "message": self.message,
        }


def _load_valid(
    output_dir: Path, task_name: str, model: type[BaseModel]
) -> BaseModel | None:
    """Load a task output if its file exists and passes schema validation.

    Schema failures are reported by the per-task validation pass; cross-task
    checks simply skip files they cannot parse.
    """
    path = output_dir / TASK_OUTPUT_FILES[task_name]
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text())
        if data is None:
            return None
        return model.model_validate(data)
    except Exception:  # noqa: BLE001 - schema pass owns the error report
        return None


def _check_paragraph_refs(
    refs: list[tuple[str, int]],
    max_paragraph: int,
    file_label: str,
    findings: list[Finding],
) -> None:
    """Flag paragraph references outside [1, max_paragraph]."""
    for location, value in refs:
        if value < 1 or value > max_paragraph:
            findings.append(
                Finding(
                    "error",
                    "paragraph_out_of_range",
                    f"{file_label}: {location} references paragraph {value}, "
                    f"but source.md has {max_paragraph} paragraphs",
                )
            )


def cross_validate_slide(output_dir: Path) -> list[Finding]:
    """Cross-task checks for the slide pipeline (task1–task7)."""
    findings: list[Finding] = []

    task2 = _load_valid(output_dir, "task2", Task2Output)
    task3 = _load_valid(output_dir, "task3", Task3Output)
    task4 = _load_valid(output_dir, "task4", Task4Output)
    task6 = _load_valid(output_dir, "task6", Task6Output)
    task7 = _load_valid(output_dir, "task7", Task7Output)

    f2 = TASK_OUTPUT_FILES["task2"]
    f3 = TASK_OUTPUT_FILES["task3"]
    f4 = TASK_OUTPUT_FILES["task4"]

    # ── 1. Dangling scene_beat_id: task4 → task2 ────────────────────────────
    if task2 is not None and task4 is not None:
        assert isinstance(task2, Task2Output) and isinstance(task4, Task4Output)
        beat_ids = {beat.beat_id for beat in (task2.scene_beats or [])}
        for alloc in task4.allocations:
            if alloc.scene_beat_id and alloc.scene_beat_id not in beat_ids:
                known = ", ".join(sorted(beat_ids)) if beat_ids else "none"
                findings.append(
                    Finding(
                        "error",
                        "dangling_scene_beat_id",
                        f"{f4}: slide {alloc.slide_number} references "
                        f"scene_beat_id '{alloc.scene_beat_id}' which does not "
                        f"exist in {f2} (known beat_ids: {known})",
                    )
                )

    # ── 2. Slide-number consistency across task3/task4/task6/task7 ──────────
    slide_sets: dict[str, set[int]] = {}
    if task3 is not None:
        assert isinstance(task3, Task3Output)
        slide_sets[f"{f3} slide_sequence"] = {
            item.slide_number for item in task3.slide_sequence
        }
        if task3.slide_count != len(task3.slide_sequence):
            findings.append(
                Finding(
                    "error",
                    "slide_count_mismatch",
                    f"{f3}: slide_count is {task3.slide_count} but "
                    f"slide_sequence has {len(task3.slide_sequence)} entries",
                )
            )
    if task4 is not None:
        assert isinstance(task4, Task4Output)
        slide_sets[f"{f4} allocations"] = {
            alloc.slide_number for alloc in task4.allocations
        }
    if task6 is not None:
        assert isinstance(task6, Task6Output)
        slide_sets[f"{TASK_OUTPUT_FILES['task6']} slides"] = {
            slide.number for slide in task6.slides
        }
    if task7 is not None:
        assert isinstance(task7, Task7Output)
        slide_sets[f"{TASK_OUTPUT_FILES['task7']} slide_prompts"] = {
            prompt.slide_number for prompt in task7.slide_prompts
        }

    if len(slide_sets) >= 2:
        labels = list(slide_sets)
        reference_label = labels[0]
        reference = slide_sets[reference_label]
        for label in labels[1:]:
            if slide_sets[label] != reference:
                missing = sorted(reference - slide_sets[label])
                extra = sorted(slide_sets[label] - reference)
                detail = []
                if missing:
                    detail.append(f"missing slides {missing}")
                if extra:
                    detail.append(f"unexpected slides {extra}")
                findings.append(
                    Finding(
                        "error",
                        "slide_set_mismatch",
                        f"{label} does not match {reference_label}: "
                        + "; ".join(detail),
                    )
                )

    # ── 3. Paragraph references vs the actual source ────────────────────────
    source_path = output_dir / "source.md"
    if source_path.exists():
        max_paragraph = len(parse_paragraphs(source_path.read_text()))
        if max_paragraph > 0:
            if task2 is not None:
                assert isinstance(task2, Task2Output)
                refs: list[tuple[str, int]] = []
                for section in task2.structural_analysis.sections:
                    # Contiguous range — checking the endpoints covers it.
                    refs.append(
                        (
                            f"section '{section.id}' paragraph_start",
                            section.paragraph_start,
                        )
                    )
                    refs.append(
                        (f"section '{section.id}' paragraph_end", section.paragraph_end)
                    )
                refs.extend(
                    (f"quotable_passage '{q.id}' source_paragraph", q.source_paragraph)
                    for q in task2.quotable_passages
                )
                for beat in task2.scene_beats or []:
                    refs.extend(
                        (f"scene_beat '{beat.beat_id}' source_paragraphs", p)
                        for p in beat.source_paragraphs
                    )
                _check_paragraph_refs(refs, max_paragraph, f2, findings)
            if task4 is not None:
                assert isinstance(task4, Task4Output)
                refs = []
                for alloc in task4.allocations:
                    label = f"slide {alloc.slide_number}"
                    if alloc.headline.source_paragraph is not None:
                        refs.append(
                            (f"{label} headline", alloc.headline.source_paragraph)
                        )
                    if (
                        alloc.subheadline is not None
                        and alloc.subheadline.source_paragraph is not None
                    ):
                        refs.append(
                            (f"{label} subheadline", alloc.subheadline.source_paragraph)
                        )
                    if (
                        alloc.quote is not None
                        and alloc.quote.source_paragraph is not None
                    ):
                        refs.append((f"{label} quote", alloc.quote.source_paragraph))
                    refs.extend(
                        (f"{label} body_text", p)
                        for p in alloc.body_text.source_paragraphs
                    )
                _check_paragraph_refs(refs, max_paragraph, f4, findings)

    # ── 4. task3 source_section → task2 sections ────────────────────────────
    if task2 is not None and task3 is not None:
        assert isinstance(task2, Task2Output) and isinstance(task3, Task3Output)
        known_sections: set[str] = set()
        for section in task2.structural_analysis.sections:
            known_sections.add(section.id)
            if section.title:
                known_sections.add(section.title)
        for item in task3.slide_sequence:
            if item.source_section not in known_sections:
                findings.append(
                    Finding(
                        "error",
                        "unknown_source_section",
                        f"{f3}: slide {item.slide_number} references "
                        f"source_section '{item.source_section}' which matches "
                        f"no section id or title in {f2} "
                        f"(known: {', '.join(sorted(known_sections))})",
                    )
                )

    # ── 5. Arc peaks/nadir/concession → existing slide numbers ──────────────
    if task3 is not None:
        assert isinstance(task3, Task3Output)
        numbers = {item.slide_number for item in task3.slide_sequence}
        arc = task3.arc_visualization
        arc_refs = [("peaks", p) for p in arc.peaks]
        if arc.nadir is not None:
            arc_refs.append(("nadir", arc.nadir))
        if arc.concession is not None:
            arc_refs.append(("concession", arc.concession))
        for field, slide_number in arc_refs:
            if slide_number not in numbers:
                findings.append(
                    Finding(
                        "error",
                        "arc_slide_missing",
                        f"{f3}: arc_visualization.{field} references slide "
                        f"{slide_number}, which is not in slide_sequence",
                    )
                )

    # ── 6. Soft content rules (warnings) ────────────────────────────────────
    if task6 is not None:
        assert isinstance(task6, Task6Output)
        f6 = TASK_OUTPUT_FILES["task6"]
        for slide in task6.slides:
            headline = slide.content.headline
            if headline and len(headline.split()) > HEADLINE_MAX_WORDS:
                findings.append(
                    Finding(
                        "warning",
                        "headline_too_long",
                        f"{f6}: slide {slide.number} headline has "
                        f"{len(headline.split())} words "
                        f"(limit {HEADLINE_MAX_WORDS}): {headline!r}",
                    )
                )
            quote = slide.content.quote
            if quote and len(quote.split()) > QUOTE_MAX_WORDS:
                findings.append(
                    Finding(
                        "warning",
                        "quote_too_long",
                        f"{f6}: slide {slide.number} quote has "
                        f"{len(quote.split())} words (limit {QUOTE_MAX_WORDS})",
                    )
                )

    return findings


# Per-pipeline cross-task validators. The slide pipeline is the priority
# (task1–task7 chain); other pipelines can register here as checks are added.
CROSS_VALIDATORS: dict[str, Callable[[Path], list[Finding]]] = {
    "slide": cross_validate_slide,
}


def cross_validate(pipeline: str, output_dir: Path) -> list[Finding]:
    """Run the cross-task checks registered for ``pipeline`` (if any)."""
    validator = CROSS_VALIDATORS.get(pipeline)
    if validator is None:
        return []
    return validator(output_dir)
