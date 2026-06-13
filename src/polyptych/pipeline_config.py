"""Pipeline-wide constants and pure helper functions.

Pipeline-type step lists, output-file maps, model-class maps, dependency
graphs, and a couple of pure helpers (resume detection, per-step logging).

This module holds no class methods; the slide and infographic mixins each
import what they need from here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from .task_registry import TASKS


# =============================================================================
# Derivation helpers
# =============================================================================
#
# The per-pipeline dicts below are derived from the TaskSpec registry. The
# registry holds output_filename / output_model / dependencies for every
# LLM-driven task; this module only adds boundary-step exceptions (images),
# which have no prompt file.


def _build_output_files(
    steps: list[str],
    boundary: dict[str, tuple[str, type[BaseModel]]],
) -> dict[str, str]:
    out: dict[str, str] = {}
    for step in steps:
        if step in boundary:
            out[step] = boundary[step][0]
            continue
        spec = TASKS.get(step)
        if spec is not None and spec.output_filename is not None:
            out[step] = spec.output_filename
    return out


def _build_models(
    steps: list[str],
    boundary: dict[str, tuple[str, type[BaseModel]]],
) -> dict[str, type[BaseModel]]:
    out: dict[str, type[BaseModel]] = {}
    for step in steps:
        if step in boundary:
            out[step] = boundary[step][1]
            continue
        spec = TASKS.get(step)
        if spec is not None and spec.output_model is not None:
            out[step] = spec.output_model
    return out


def _build_step_deps(
    steps: list[str],
    boundary_deps: dict[str, list[str]],
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for step in steps:
        if step in boundary_deps:
            out[step] = list(boundary_deps[step])
            continue
        spec = TASKS.get(step)
        if spec is not None:
            out[step] = list(spec.dependencies)
    return out


# =============================================================================
# Task (slide) Pipeline Steps
# =============================================================================

ALL_STEPS = ["task1", "task2", "task3", "task4", "task5", "task6", "task7", "images"]
StepName = Literal[
    "task1", "task2", "task3", "task4", "task5", "task6", "task7", "images"
]

_SLIDE_BOUNDARY_DEPS: dict[str, list[str]] = {"images": ["task7"]}

STEP_DEPENDENCIES = _build_step_deps(ALL_STEPS, _SLIDE_BOUNDARY_DEPS)
TASK_OUTPUT_FILES = _build_output_files(ALL_STEPS, {})
TASK_MODELS = _build_models(ALL_STEPS, {})


# =============================================================================
# Infographic Pipeline Steps
# =============================================================================

INFOGRAPHIC_STEPS = ["i0", "i1", "i2", "images"]
InfographicStepName = Literal["i0", "i1", "i2", "images"]

_INFOGRAPHIC_BOUNDARY_DEPS: dict[str, list[str]] = {"images": ["i2"]}

INFOGRAPHIC_OUTPUT_FILES = _build_output_files(INFOGRAPHIC_STEPS, {})
INFOGRAPHIC_MODELS = _build_models(INFOGRAPHIC_STEPS, {})
INFOGRAPHIC_STEP_DEPENDENCIES: dict[str, list[str]] = _build_step_deps(
    INFOGRAPHIC_STEPS,
    _INFOGRAPHIC_BOUNDARY_DEPS,
)


# =============================================================================
# Pure helpers
# =============================================================================


def find_resume_step(
    output_dir: Path,
    steps: list[str],
    output_files: dict[str, str],
    model_classes: dict[str, type],
) -> str | None:
    """Find the first step that needs to be (re)run based on existing outputs.

    Walks steps in order. For each step that has a known output file,
    checks that the file exists, is non-empty, parses as valid YAML,
    and validates against its Pydantic model. The first step with a
    missing or invalid output is the resume point.

    Steps not in output_files (like 'images') are untracked
    boundaries — if reached, all prior tracked steps are valid.

    Returns None if every tracked step has valid output.
    """
    from pydantic import ValidationError

    for step in steps:
        if step not in output_files:
            # Untracked step (images) — all prior steps valid
            return None
        filepath = output_dir / output_files[step]
        try:
            if not filepath.exists():
                return step
            content = filepath.read_text()
            if not content.strip():
                return step
            data = yaml.safe_load(content)
            if data is None:
                return step
            if step in model_classes:
                model_classes[step].model_validate(data)
        except (yaml.YAMLError, ValidationError, IOError):
            return step
    return None


def _make_step_logger(step: str):
    """Return a log function that prefixes messages with [step]."""

    def log(msg: str) -> None:
        print(f"[{step}] {msg}")

    return log
