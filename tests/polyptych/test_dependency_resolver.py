"""Tests for the generic dependency resolver on ``SlidePipelineBase``.

``_load_task_output_generic`` and ``_load_dependencies_generic`` replaced the
eight near-identical ``_load_<pipeline>_*`` method pairs (TASK-38). These tests
exercise the resolver directly with a tiny fake model and hand-built maps so
the error paths (missing file, schema mismatch, untracked dependency skip,
attribute-prefix handling) are covered independently of any real task schema.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from polyptych.model_config import ModelConfig
from polyptych.pipeline import SlidePipeline


class _FakeOutput(BaseModel):
    value: int


_OUTPUT_FILES = {"fake": "fake-out.yaml"}
_MODELS: dict[str, type[BaseModel]] = {"fake": _FakeOutput}
_STEP_DEPS = {
    "needs_fake": ["fake"],
    "needs_untracked": ["fake", "untracked"],
    "images": ["untracked"],
}


@pytest.fixture
def pipeline(tmp_path: Path, mock_client, source_text: str) -> SlidePipeline:
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)
    mc = ModelConfig(
        providers={"gemini": {"fast": "test-model", "thinking": "test-model"}},
        tasks={"a0": "fast", "task1": "fast"},
        max_output_tokens={},
        thinking_budget={},
    )
    p = SlidePipeline(
        source_path=source_file,
        output_dir=tmp_path / "output",
        model_config=mc,
        text_provider="gemini",
        text_fallback=["none"],
    )
    p.text_client = mock_client
    return p


# ---------------------------------------------------------------------------
# _load_task_output_generic
# ---------------------------------------------------------------------------


class TestLoadTaskOutputGeneric:
    def test_loads_and_sets_prefixed_attribute(self, pipeline: SlidePipeline):
        pipeline._save_yaml({"value": 7}, "fake-out.yaml")

        loaded = pipeline._load_task_output_generic(
            "fake",
            output_files=_OUTPUT_FILES,
            models=_MODELS,
        )

        assert loaded is True
        assert pipeline.task_fake_output.value == 7  # type: ignore[attr-defined]

    def test_empty_prefix_omits_task_prefix(self, pipeline: SlidePipeline):
        pipeline._save_yaml({"value": 1}, "fake-out.yaml")

        pipeline._load_task_output_generic(
            "fake",
            output_files=_OUTPUT_FILES,
            models=_MODELS,
            attr_prefix="",
        )

        assert pipeline.fake_output.value == 1  # type: ignore[attr-defined]

    def test_untracked_task_returns_false(self, pipeline: SlidePipeline):
        assert (
            pipeline._load_task_output_generic(
                "nope",
                output_files=_OUTPUT_FILES,
                models=_MODELS,
            )
            is False
        )

    def test_missing_file_returns_false(self, pipeline: SlidePipeline):
        # 'fake' is tracked but no YAML was written.
        assert (
            pipeline._load_task_output_generic(
                "fake",
                output_files=_OUTPUT_FILES,
                models=_MODELS,
            )
            is False
        )

    def test_schema_mismatch_raises_validation_error(self, pipeline: SlidePipeline):
        pipeline._save_yaml({"wrong_field": "x"}, "fake-out.yaml")

        with pytest.raises(ValidationError):
            pipeline._load_task_output_generic(
                "fake",
                output_files=_OUTPUT_FILES,
                models=_MODELS,
            )


# ---------------------------------------------------------------------------
# _load_dependencies_generic
# ---------------------------------------------------------------------------


class TestLoadDependenciesGeneric:
    def _kwargs(self) -> dict:
        return {
            "step_deps": _STEP_DEPS,
            "output_files": _OUTPUT_FILES,
            "models": _MODELS,
            "pipeline_label": "testpipe",
        }

    def test_loads_present_dependency(self, pipeline: SlidePipeline):
        pipeline._save_yaml({"value": 3}, "fake-out.yaml")

        pipeline._load_dependencies_generic("needs_fake", **self._kwargs())

        assert pipeline.task_fake_output.value == 3  # type: ignore[attr-defined]

    def test_missing_dependency_raises_with_message(self, pipeline: SlidePipeline):
        with pytest.raises(FileNotFoundError, match="missing required outputs") as exc:
            pipeline._load_dependencies_generic("needs_fake", **self._kwargs())

        # Error names the offending pipeline/step and the expected file path.
        assert "testpipe step 'needs_fake'" in str(exc.value)
        assert "fake-out.yaml" in str(exc.value)

    def test_untracked_dependency_is_skipped(self, pipeline: SlidePipeline):
        pipeline._save_yaml({"value": 5}, "fake-out.yaml")

        # 'untracked' has no entry in output_files (cf. blog's image-only b3),
        # so it must be skipped rather than treated as missing.
        pipeline._load_dependencies_generic("needs_untracked", **self._kwargs())

        assert pipeline.task_fake_output.value == 5  # type: ignore[attr-defined]

    def test_step_with_only_untracked_deps_never_raises(self, pipeline: SlidePipeline):
        # 'images' depends solely on an untracked step — nothing to load, no raise.
        pipeline._load_dependencies_generic("images", **self._kwargs())
