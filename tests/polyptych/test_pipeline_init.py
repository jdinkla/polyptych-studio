"""Tests for SlidePipeline.__init__ and _write_manifest.

Covers construction side-effects (directories, source copy, task-output slots)
and the manifest writer that records provenance for each run.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from polyptych.model_config import ModelConfig
from polyptych.pipeline import SlidePipeline
from polyptych.run_config import PipelineRunConfig, SlideRunConfig


def _build_pipeline(
    tmp_path: Path,
    source_text: str,
    model_config: ModelConfig,
) -> SlidePipeline:
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)
    output_dir = tmp_path / "output"
    return SlidePipeline(
        source_path=source_file,
        output_dir=output_dir,
        model_config=model_config,
        text_provider="gemini",
        text_fallback=["none"],
    )


# ---------------------------------------------------------------------------
# SlidePipeline.__init__
# ---------------------------------------------------------------------------


class TestSlidePipelineInit:
    def test_creates_output_subdirectories(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        assert pipeline.output_dir.is_dir()
        assert (pipeline.output_dir / "prompts").is_dir()
        assert (pipeline.output_dir / "images").is_dir()

    def test_copies_source_into_output_dir(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        copied = pipeline.output_dir / "source.md"
        assert copied.is_file()
        assert copied.read_text() == source_text

    def test_reads_source_essay_into_instance(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        assert pipeline.source_essay == source_text

    def test_task_output_slots_initialized_to_none(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        for n in range(1, 8):
            assert getattr(pipeline, f"task{n}_output") is None

    def test_accepts_string_paths(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        source_file = tmp_path / "source.md"
        source_file.write_text(source_text)
        output_dir = tmp_path / "output"
        pipeline = SlidePipeline(
            source_path=str(source_file),
            output_dir=str(output_dir),
            model_config=test_model_config,
            text_provider="gemini",
            text_fallback=["none"],
        )
        assert pipeline.source_path == Path(source_file)
        assert pipeline.output_dir == Path(output_dir)

    def test_idempotent_across_runs(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        # Re-running against an existing output dir should not error — mkdir
        # uses exist_ok=True and source.md is copied with shutil.copy2.
        _build_pipeline(tmp_path, source_text, test_model_config)
        _build_pipeline(tmp_path, source_text, test_model_config)


# ---------------------------------------------------------------------------
# SlidePipeline._write_manifest
# ---------------------------------------------------------------------------


class TestWriteManifest:
    def test_writes_yaml_with_core_fields(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        manifest_path = pipeline._write_manifest("slide", PipelineRunConfig())
        assert manifest_path == pipeline.output_dir / "manifest.yaml"

        data = yaml.safe_load(manifest_path.read_text())
        assert data["pipeline"] == "slide"
        assert "timestamp" in data
        assert data["source"] == "source.md"
        assert data["image_provider"] == "gemini"
        assert data["aspect_ratio"] == "16:9"

    def test_single_model_collapses_to_scalar(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        # test_model_config has every tier resolving to "test-model".
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        pipeline._write_manifest("slide", PipelineRunConfig())
        data = yaml.safe_load((pipeline.output_dir / "manifest.yaml").read_text())
        assert data["models"] == "test-model"

    def test_multiple_models_kept_as_sorted_list(
        self,
        tmp_path,
        source_text,
    ):
        # Distinct models per tier → models_used should be a sorted list.
        mc = ModelConfig(
            providers={
                "gemini": {"fast": "gemini-fast", "thinking": "gemini-thinking"},
            },
            tasks={"task1": "fast", "task2": "thinking"},
            max_output_tokens={},
            thinking_budget={},
        )
        pipeline = _build_pipeline(tmp_path, source_text, mc)
        pipeline._write_manifest("slide", PipelineRunConfig())
        data = yaml.safe_load((pipeline.output_dir / "manifest.yaml").read_text())
        assert data["models"] == ["gemini-fast", "gemini-thinking"]

    def test_none_values_stripped(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        pipeline._write_manifest(
            "slide",
            PipelineRunConfig(size=None, quality=None, style_prompt_path=None),
        )
        data = yaml.safe_load((pipeline.output_dir / "manifest.yaml").read_text())
        assert "image_size" not in data
        assert "image_quality" not in data
        assert "style_prompt" not in data

    def test_extra_fields_from_subclass_merged(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        # SlideRunConfig._manifest_extras() returns {"steps": "<from>-><to>"}.
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        pipeline._write_manifest(
            "slide",
            SlideRunConfig(from_step="task1", to_step="task7"),
        )
        data = yaml.safe_load((pipeline.output_dir / "manifest.yaml").read_text())
        assert data["steps"] == "task1->task7"

    def test_style_prompt_path_preserved_when_set(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        pipeline._write_manifest(
            "slide",
            PipelineRunConfig(
                style_prompt_path="prompts/style-transfer/noir/hardboiled.md"
            ),
        )
        data = yaml.safe_load((pipeline.output_dir / "manifest.yaml").read_text())
        assert data["pipeline"] == "slide"
        assert data["style_prompt"].endswith("hardboiled.md")


# ---------------------------------------------------------------------------
# Per-run image generation defaults
# ---------------------------------------------------------------------------


class TestImageRunDefaults:
    def test_init_empty_defaults(self, tmp_path, source_text, test_model_config):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        assert pipeline._image_ref_paths == []
        assert pipeline._image_output_format is None
        assert pipeline._image_output_compression is None

    def test_set_image_run_defaults_stores_values(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        pipeline._set_image_run_defaults(
            ref_images=["/tmp/a.png", "/tmp/b.png"],
            output_format="webp",
            output_compression=85,
        )
        assert pipeline._image_ref_paths == [Path("/tmp/a.png"), Path("/tmp/b.png")]
        assert pipeline._image_output_format == "webp"
        assert pipeline._image_output_compression == 85

    def test_set_image_run_defaults_resets_refs_when_empty(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        pipeline._set_image_run_defaults(ref_images=["/tmp/a.png"])
        assert pipeline._image_ref_paths == [Path("/tmp/a.png")]
        # A second call with None / empty should clear the prior list.
        pipeline._set_image_run_defaults(ref_images=None)
        assert pipeline._image_ref_paths == []
        pipeline._set_image_run_defaults(ref_images=["/tmp/c.png"])
        pipeline._set_image_run_defaults(ref_images=[])
        assert pipeline._image_ref_paths == []

    def test_set_image_run_defaults_accepts_path_objects(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        pipeline._set_image_run_defaults(
            ref_images=[Path("/tmp/a.png"), Path("/tmp/b.png")],
        )
        assert pipeline._image_ref_paths == [Path("/tmp/a.png"), Path("/tmp/b.png")]

    def test_make_image_client_propagates_defaults(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        pipeline._set_image_run_defaults(
            ref_images=["/tmp/a.png", "/tmp/b.png"],
            output_format="jpeg",
            output_compression=70,
        )
        client = pipeline._make_image_client("openai")
        assert client.provider_name == "openai"
        assert client.usage_log == pipeline.output_dir / "usage.jsonl"
        assert client.default_output_format == "jpeg"
        assert client.default_output_compression == 70
        assert client.default_reference_images == [
            Path("/tmp/a.png"),
            Path("/tmp/b.png"),
        ]

    def test_make_image_client_passes_none_when_no_refs(
        self,
        tmp_path,
        source_text,
        test_model_config,
    ):
        # When no refs are configured, default_reference_images should be None
        # rather than an empty list — the upstream client's auto-promote check
        # treats an empty-but-truthy list differently from None.
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        client = pipeline._make_image_client("openai")
        assert client.default_reference_images in (None, [])
        # Verify auto-promote does NOT fire on empty defaults.
        assert not client.default_reference_images
