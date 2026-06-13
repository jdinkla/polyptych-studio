"""Tests for the task registry and the prompt_loader wrappers."""

from pathlib import Path

import pytest
import yaml

from polyptych.prompt_loader import (
    INFOGRAPHIC_TASK_PROMPTS,
    TASK_PROMPTS,
    get_prompts_dir,
    load_infographic_task_prompt,
    load_prompt_for,
    load_task_prompt,
)
from polyptych.pipeline_config import (
    ALL_STEPS,
    INFOGRAPHIC_MODELS,
    INFOGRAPHIC_OUTPUT_FILES,
    INFOGRAPHIC_STEP_DEPENDENCIES,
    INFOGRAPHIC_STEPS,
    STEP_DEPENDENCIES,
    TASK_MODELS,
    TASK_OUTPUT_FILES,
)
from polyptych.task_registry import (
    TASKS,
    TaskSpec,
    get_task,
    tasks_for_pipeline,
)


class TestRegistryShape:
    def test_every_task_is_uniquely_named(self):
        assert len(TASKS) == len({spec.name for spec in TASKS.values()})

    def test_get_task_returns_spec(self):
        spec = get_task("task1")
        assert isinstance(spec, TaskSpec)
        assert spec.pipeline == "slide"

    def test_get_task_raises_on_unknown_name(self):
        with pytest.raises(KeyError, match="Unknown task"):
            get_task("does-not-exist")

    def test_tasks_for_pipeline_preserves_registration_order(self):
        slide = [s.name for s in tasks_for_pipeline("slide")]
        assert slide == [f"task{n}" for n in range(1, 8)]

    def test_each_pipeline_has_at_least_one_task(self):
        for pipeline in ("slide", "infographic"):
            assert tasks_for_pipeline(pipeline)


class TestPromptResolution:
    def test_plain_task_resolves_base_filename(self):
        spec = get_task("task1")
        assert spec.resolve_prompt_filename() == "task-01-genre-classification.md"

    def test_genre_variant_substitutes_into_filename(self):
        spec = get_task("task6")
        assert (
            spec.resolve_prompt_filename(genre="fiction")
            == "task-06-slide-specification-fiction.md"
        )

    def test_genre_ignored_when_task_does_not_support_it(self):
        spec = get_task("task1")
        assert (
            spec.resolve_prompt_filename(genre="fiction")
            == "task-01-genre-classification.md"
        )


class TestRegistryMatchesDisk:
    """Every non-variant prompt file referenced by the registry must exist."""

    def test_base_prompts_exist(self):
        prompts_dir = get_prompts_dir()
        for spec in TASKS.values():
            if spec.supports_subtype:
                # Base filename is a stem; each subtype has its own file — covered separately.
                continue
            path = prompts_dir / spec.resolve_prompt_filename()
            assert path.exists(), f"missing prompt file for {spec.name}: {path}"


class TestLegacyWrappers:
    """Back-compat shims must keep returning exactly what callers expect."""

    def test_task_prompts_dict_shape(self):
        assert set(TASK_PROMPTS) == set(range(1, 8))
        assert TASK_PROMPTS[1] == "task-01-genre-classification.md"

    def test_infographic_prompts_covers_i0_through_i2(self):
        assert set(INFOGRAPHIC_TASK_PROMPTS) == {
            "i0",
            "i1",
            "i2",
            "i2_critique",
            "i2_refine",
        }

    def test_load_task_prompt_returns_content(self):
        text = load_task_prompt(1)
        assert text.strip()

    def test_load_task_prompt_rejects_out_of_range(self):
        with pytest.raises(ValueError, match="Invalid task number"):
            load_task_prompt(99)

    def test_unified_loader_matches_legacy_for_task1(self):
        assert load_prompt_for("task1") == load_task_prompt(1)

    def test_unified_loader_matches_legacy_for_infographic_i0(self):
        assert load_prompt_for("i0") == load_infographic_task_prompt("i0")


class TestCrossCheckWithModelConfig:
    """Task names used in model_config.yaml should line up with the registry."""

    @pytest.fixture
    def model_config(self) -> dict:
        path = Path(__file__).resolve().parents[2] / "model_config.yaml"
        with path.open() as f:
            return yaml.safe_load(f)

    def test_every_pipeline_task_in_model_config_is_registered(self, model_config):
        # Excluded: 'enrichment' is a shared helper prompt,
        # not a pipeline task in the registry.
        excluded = {
            "enrichment",
        }
        for task_name in model_config["tasks"]:
            if task_name in excluded:
                continue
            assert task_name in TASKS, (
                f"model_config.yaml references unknown task {task_name!r}"
            )


class TestRegistryFieldsMatchPipelineConfig:
    """The TaskSpec fields (output_filename / output_model / dependencies)
    must agree with the pipeline_config dicts. Boundary steps (images) have no
    TaskSpec entry — they're tracked in pipeline_config alone — and are skipped
    here.
    """

    PIPELINE_CONSTANTS = [
        # (steps tuple, output_files dict, models dict, deps dict)
        (ALL_STEPS, TASK_OUTPUT_FILES, TASK_MODELS, STEP_DEPENDENCIES),
        (
            INFOGRAPHIC_STEPS,
            INFOGRAPHIC_OUTPUT_FILES,
            INFOGRAPHIC_MODELS,
            INFOGRAPHIC_STEP_DEPENDENCIES,
        ),
    ]

    def test_output_filename_matches_pipeline_config(self):
        for _steps, output_files, _models, _deps in self.PIPELINE_CONSTANTS:
            for step, filename in output_files.items():
                spec = TASKS.get(step)
                if spec is None:
                    continue  # boundary step
                assert spec.output_filename == filename, (
                    f"{step}.output_filename={spec.output_filename!r} but "
                    f"pipeline_config has {filename!r}"
                )

    def test_output_model_matches_pipeline_config(self):
        for _steps, _output_files, models, _deps in self.PIPELINE_CONSTANTS:
            for step, model_cls in models.items():
                spec = TASKS.get(step)
                if spec is None:
                    continue
                assert spec.output_model is model_cls, (
                    f"{step}.output_model={spec.output_model} but "
                    f"pipeline_config has {model_cls}"
                )

    def test_dependencies_match_pipeline_config(self):
        for _steps, _output_files, _models, deps in self.PIPELINE_CONSTANTS:
            for step, expected in deps.items():
                spec = TASKS.get(step)
                if spec is None:
                    continue
                assert list(spec.dependencies) == expected, (
                    f"{step}.dependencies={list(spec.dependencies)} but "
                    f"pipeline_config has {expected}"
                )

    def test_step_order_matches_owning_pipeline_steps_index(self):
        # step_order is the 1-based index of the task within its OWNING pipeline's
        # *_STEPS tuple.
        owning_steps = {
            "slide": ALL_STEPS,
            "infographic": INFOGRAPHIC_STEPS,
        }
        for spec in TASKS.values():
            if spec.step_order is None:
                continue
            steps = owning_steps[spec.pipeline]
            assert spec.name in steps, (
                f"{spec.name} (pipeline={spec.pipeline}) has step_order={spec.step_order} "
                f"but is not in {spec.pipeline.upper()}_STEPS"
            )
            expected = steps.index(spec.name) + 1
            assert spec.step_order == expected, (
                f"{spec.name}.step_order={spec.step_order} but its index in "
                f"{spec.pipeline.upper()}_STEPS is {expected - 1} (expected step_order={expected})"
            )

    def test_critique_and_refine_variants_have_no_step_order(self):
        # Critique/refine sub-tasks are invoked within their parent step and
        # should not appear in the linear pipeline order.
        for spec in TASKS.values():
            if spec.name.endswith("_critique") or spec.name.endswith("_refine"):
                assert spec.step_order is None, (
                    f"{spec.name} should not have step_order (it's a sub-task)"
                )
                assert spec.output_filename is None
                assert spec.output_model is None
                assert spec.dependencies == ()

    def test_every_tracked_step_with_output_is_registered_or_boundary(self):
        # Sanity: every key in *_OUTPUT_FILES must either be in the registry
        # with an output_filename, or be a known boundary.
        boundary_outputs: set[str] = set()
        for _steps, output_files, _models, _deps in self.PIPELINE_CONSTANTS:
            for step in output_files:
                if step in boundary_outputs:
                    continue
                assert step in TASKS, f"{step} in *_OUTPUT_FILES but not in registry"
                assert TASKS[step].output_filename is not None
