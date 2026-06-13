"""Tests for pipeline_config.py pure helpers and derived constant tables.

find_resume_step is covered separately in test_pipeline_resume.py. This file
pins the remaining pure helpers and the registry-derived per-pipeline dicts.
"""

from __future__ import annotations

from polyptych.pipeline_config import (
    ALL_STEPS,
    INFOGRAPHIC_OUTPUT_FILES,
    STEP_DEPENDENCIES,
    TASK_MODELS,
    TASK_OUTPUT_FILES,
    _make_step_logger,
)


# =============================================================================
# Derived constant tables
# =============================================================================


class TestDerivedTables:
    def test_slide_steps_have_output_files_and_models(self):
        # Every task step (task1..task7) is registry-backed; "images" is untracked.
        for step in ALL_STEPS:
            if step == "images":
                assert step not in TASK_OUTPUT_FILES
            else:
                assert step in TASK_OUTPUT_FILES
                assert step in TASK_MODELS

    def test_slide_boundary_dep_images_depends_on_task7(self):
        # The "images" boundary step is wired by hand (no prompt file).
        assert STEP_DEPENDENCIES["images"] == ["task7"]

    def test_task2_depends_on_task1(self):
        assert "task1" in STEP_DEPENDENCIES["task2"]

    def test_infographic_images_untracked(self):
        # i0/i1/i2 are tracked; images is a boundary step with no output file.
        assert "i2" in INFOGRAPHIC_OUTPUT_FILES
        assert "images" not in INFOGRAPHIC_OUTPUT_FILES


# =============================================================================
# _make_step_logger
# =============================================================================


class TestMakeStepLogger:
    def test_prefixes_with_step_name(self, capsys):
        log = _make_step_logger("task3")
        log("hello world")
        assert capsys.readouterr().out == "[task3] hello world\n"
