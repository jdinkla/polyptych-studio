"""Tests for slide pipeline (Tasks 1-7) step range, dependency loading, and flow control."""

from __future__ import annotations

import pytest
import yaml

from polyptych.pipeline import SlidePipeline, TASK_OUTPUT_FILES
from polyptych.run_config import SlideRunConfig

from ..mock_client import MockTextClient
from .factories import (
    make_task1_output,
    make_task2_output,
    make_task3_output,
    make_task4_output,
    make_task5_output,
    make_task6_output,
    make_task7_output,
)


def _write_yaml(pipeline: SlidePipeline, task_name: str, model_obj) -> None:
    """Write a task output YAML to the pipeline's output directory."""
    path = pipeline.output_dir / TASK_OUTPUT_FILES[task_name]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(model_obj.model_dump(), f, default_flow_style=False)


# =============================================================================
# Step range validation
# =============================================================================


class TestStepRangeValidation:
    def test_invalid_start_step_raises(self, slide_pipeline: SlidePipeline):
        with pytest.raises(ValueError):
            slide_pipeline.run_from(SlideRunConfig(from_step="BOGUS", to_step="task1"))

    def test_invalid_end_step_raises(self, slide_pipeline: SlidePipeline):
        with pytest.raises(ValueError):
            slide_pipeline.run_from(SlideRunConfig(from_step="task1", to_step="BOGUS"))

    def test_start_after_end_raises(self, slide_pipeline: SlidePipeline):
        with pytest.raises(ValueError, match="comes after"):
            slide_pipeline.run_from(SlideRunConfig(from_step="task3", to_step="task1"))


# =============================================================================
# Single-step runs
# =============================================================================


class TestSingleStepRuns:
    def test_task1_only(
        self,
        slide_pipeline: SlidePipeline,
        mock_client: MockTextClient,
    ):
        """Run only task1 — one structured call, YAML written."""
        mock_client.register_structured("task1", make_task1_output())

        slide_pipeline.run_from(SlideRunConfig(from_step="task1", to_step="task1"))

        assert mock_client.call_count("structured:task1") == 1
        assert (slide_pipeline.output_dir / TASK_OUTPUT_FILES["task1"]).exists()

    def test_task2_loads_task1(
        self,
        slide_pipeline: SlidePipeline,
        mock_client: MockTextClient,
    ):
        """Running task2 alone loads task1 from disk."""
        _write_yaml(slide_pipeline, "task1", make_task1_output())
        mock_client.register_structured("task2", make_task2_output())

        slide_pipeline.run_from(SlideRunConfig(from_step="task2", to_step="task2"))

        assert mock_client.call_count("structured:task1") == 0
        assert mock_client.call_count("structured:task2") == 1
        assert (slide_pipeline.output_dir / TASK_OUTPUT_FILES["task2"]).exists()
        assert slide_pipeline.task1_output is not None

    def test_task5_loads_task1_task2_task4(
        self,
        slide_pipeline: SlidePipeline,
        mock_client: MockTextClient,
    ):
        """task5 depends on task1, task2, task4 — all must load; task3 is NOT a dep."""
        _write_yaml(slide_pipeline, "task1", make_task1_output())
        _write_yaml(slide_pipeline, "task2", make_task2_output())
        _write_yaml(slide_pipeline, "task4", make_task4_output())
        mock_client.register_structured("task5", make_task5_output())

        slide_pipeline.run_from(SlideRunConfig(from_step="task5", to_step="task5"))

        assert mock_client.call_count("structured:task5") == 1
        assert slide_pipeline.task1_output is not None
        assert slide_pipeline.task2_output is not None
        assert slide_pipeline.task4_output is not None

    def test_task5_receives_style_prompt_from_config(
        self,
        slide_pipeline: SlidePipeline,
        mock_client: MockTextClient,
    ):
        """--style preset text is threaded into the task5 user prompt."""
        _write_yaml(slide_pipeline, "task1", make_task1_output())
        _write_yaml(slide_pipeline, "task2", make_task2_output())
        _write_yaml(slide_pipeline, "task4", make_task4_output())
        mock_client.register_structured("task5", make_task5_output())

        style_file = slide_pipeline.output_dir / "style.md"
        style_file.write_text("Stark noir black-and-white ink style.")

        slide_pipeline.run_from(
            SlideRunConfig(
                from_step="task5",
                to_step="task5",
                style_prompt_path=str(style_file),
            )
        )

        call = mock_client.last_call("task5")
        assert "## Style Transfer Preset" in call["prompt"]
        assert "Stark noir black-and-white ink style." in call["prompt"]

    def test_task5_prompt_has_no_style_section_without_style(
        self,
        slide_pipeline: SlidePipeline,
        mock_client: MockTextClient,
    ):
        """Without --style, the task5 user prompt carries no preset section."""
        _write_yaml(slide_pipeline, "task1", make_task1_output())
        _write_yaml(slide_pipeline, "task2", make_task2_output())
        _write_yaml(slide_pipeline, "task4", make_task4_output())
        mock_client.register_structured("task5", make_task5_output())

        slide_pipeline.run_from(SlideRunConfig(from_step="task5", to_step="task5"))

        call = mock_client.last_call("task5")
        assert "Style Transfer Preset" not in call["prompt"]


# =============================================================================
# Dependency loading
# =============================================================================


class TestDependencyLoading:
    def test_missing_dependency_raises_filenotfound(
        self,
        slide_pipeline: SlidePipeline,
    ):
        """Running task3 without task1/task2 on disk raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="missing required outputs"):
            slide_pipeline.run_from(SlideRunConfig(from_step="task3", to_step="task3"))

    def test_deps_skipped_when_in_range(
        self,
        slide_pipeline: SlidePipeline,
        mock_client: MockTextClient,
    ):
        """Steps in the run range are not required to be on disk (will be generated)."""
        mock_client.register_structured("task1", make_task1_output())
        mock_client.register_structured("task2", make_task2_output())
        mock_client.register_structured("task3", make_task3_output())

        slide_pipeline.run_from(SlideRunConfig(from_step="task1", to_step="task3"))

        assert mock_client.call_count("structured:task1") == 1
        assert mock_client.call_count("structured:task2") == 1
        assert mock_client.call_count("structured:task3") == 1

    def test_partial_range_loads_out_of_range_deps(
        self,
        slide_pipeline: SlidePipeline,
        mock_client: MockTextClient,
    ):
        """Running task3->task4 loads task1, task2 from disk but not task3 (regenerated)."""
        _write_yaml(slide_pipeline, "task1", make_task1_output())
        _write_yaml(slide_pipeline, "task2", make_task2_output())
        # task3 exists on disk but should still be regenerated since in range
        _write_yaml(slide_pipeline, "task3", make_task3_output())

        mock_client.register_structured("task3", make_task3_output())
        mock_client.register_structured("task4", make_task4_output())

        slide_pipeline.run_from(SlideRunConfig(from_step="task3", to_step="task4"))

        assert mock_client.call_count("structured:task1") == 0
        assert mock_client.call_count("structured:task2") == 0
        assert mock_client.call_count("structured:task3") == 1
        assert mock_client.call_count("structured:task4") == 1


# =============================================================================
# Multi-step flow
# =============================================================================


class TestMultiStepFlow:
    def test_task1_through_task3(
        self,
        slide_pipeline: SlidePipeline,
        mock_client: MockTextClient,
    ):
        """Running task1->task3 writes three YAMLs in order."""
        mock_client.register_structured("task1", make_task1_output())
        mock_client.register_structured("task2", make_task2_output())
        mock_client.register_structured("task3", make_task3_output())

        slide_pipeline.run_from(SlideRunConfig(from_step="task1", to_step="task3"))

        for name in ("task1", "task2", "task3"):
            assert (slide_pipeline.output_dir / TASK_OUTPUT_FILES[name]).exists()
        # task4-task7 outputs should NOT exist
        for name in ("task4", "task5", "task6", "task7"):
            assert not (slide_pipeline.output_dir / TASK_OUTPUT_FILES[name]).exists()

    def test_task1_through_task7_writes_prompt_files(
        self,
        slide_pipeline: SlidePipeline,
        mock_client: MockTextClient,
    ):
        """Full text pipeline (task1->task7) writes per-slide prompt YAMLs."""
        mock_client.register_structured("task1", make_task1_output())
        mock_client.register_structured("task2", make_task2_output())
        mock_client.register_structured("task3", make_task3_output(slide_count=3))
        mock_client.register_structured("task4", make_task4_output(slide_count=3))
        mock_client.register_structured("task5", make_task5_output())
        mock_client.register_structured("task6", make_task6_output(slide_count=3))
        mock_client.register_structured("task7", make_task7_output(slide_count=3))

        slide_pipeline.run_from(SlideRunConfig(from_step="task1", to_step="task7"))

        for name in ("task1", "task2", "task3", "task4", "task5", "task6", "task7"):
            assert (slide_pipeline.output_dir / TASK_OUTPUT_FILES[name]).exists()

        prompts_dir = slide_pipeline.output_dir / "prompts"
        prompt_files = sorted(prompts_dir.glob("slide-*-prompt.yaml"))
        assert len(prompt_files) == 3


# =============================================================================
# Mode override (task1)
# =============================================================================


class TestModeOverride:
    def test_mode_override_passed_to_task1_prompt(
        self,
        slide_pipeline: SlidePipeline,
        mock_client: MockTextClient,
    ):
        """Mode override should appear in the task1 user prompt."""
        mock_client.register_structured("task1", make_task1_output(genre="fiction"))

        slide_pipeline.run_from(
            SlideRunConfig(
                from_step="task1",
                to_step="task1",
                mode="fiction",
            )
        )

        call = mock_client.last_call("task1")
        assert "fiction" in call["prompt"]
        assert "Genre Override" in call["prompt"]

    def test_mode_auto_no_override_in_prompt(
        self,
        slide_pipeline: SlidePipeline,
        mock_client: MockTextClient,
    ):
        """mode='auto' should not inject override instructions."""
        mock_client.register_structured("task1", make_task1_output())

        slide_pipeline.run_from(
            SlideRunConfig(
                from_step="task1",
                to_step="task1",
                mode="auto",
            )
        )

        call = mock_client.last_call("task1")
        assert "Genre Override" not in call["prompt"]


# =============================================================================
# Manifest
# =============================================================================


class TestManifest:
    def test_manifest_written(
        self,
        slide_pipeline: SlidePipeline,
        mock_client: MockTextClient,
    ):
        """run_from should write manifest.yaml with the expected fields."""
        mock_client.register_structured("task1", make_task1_output())

        slide_pipeline.run_from(SlideRunConfig(from_step="task1", to_step="task1"))

        manifest_path = slide_pipeline.output_dir / "manifest.yaml"
        assert manifest_path.exists()
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        assert manifest["pipeline"] == "slide"
        assert "timestamp" in manifest
        assert manifest["steps"] == "task1->task1"
