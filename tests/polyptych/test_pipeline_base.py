"""Tests for SlidePipeline base-class YAML I/O.

Focuses on the atomic _save_yaml guarantee: a crash mid-write must never
leave a half-written task output behind for the resume logic to load.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import polyptych.pipeline_base as pipeline_base
from polyptych.model_config import ModelConfig
from polyptych.pipeline import SlidePipeline


def _build_pipeline(
    tmp_path: Path, source_text: str, model_config: ModelConfig
) -> SlidePipeline:
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)
    return SlidePipeline(
        source_path=source_file,
        output_dir=tmp_path / "output",
        model_config=model_config,
        text_provider="gemini",
        text_fallback=["none"],
    )


class TestSourceCopy:
    def test_resume_with_in_dir_source_does_not_raise(
        self, tmp_path, source_text, test_model_config
    ):
        """Resuming a run by pointing source_path at the output dir's own
        source.md must not crash. The first run writes <output_dir>/source.md,
        so a natural resume command passes that exact path back in; copying it
        onto itself used to raise shutil.SameFileError before any work ran."""
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True)
        in_dir_source = output_dir / "source.md"
        in_dir_source.write_text(source_text)

        pipeline = SlidePipeline(
            source_path=in_dir_source,
            output_dir=output_dir,
            model_config=test_model_config,
            text_provider="gemini",
            text_fallback=["none"],
        )

        # The self-copy is skipped, not attempted: the in-dir source survives
        # untouched and the pipeline still loaded it.
        assert (output_dir / "source.md").read_text() == source_text
        assert pipeline.source_essay == source_text

    def test_fresh_run_copies_source_into_output_dir(
        self, tmp_path, source_text, test_model_config
    ):
        """A normal run (source outside the output dir) still copies source.md
        into the output directory."""
        source_file = tmp_path / "essay.md"
        source_file.write_text(source_text)
        pipeline = SlidePipeline(
            source_path=source_file,
            output_dir=tmp_path / "output",
            model_config=test_model_config,
            text_provider="gemini",
            text_fallback=["none"],
        )
        assert (pipeline.output_dir / "source.md").read_text() == source_text


class TestSaveYamlAtomic:
    def test_save_writes_file_and_leaves_no_temp(
        self, tmp_path, source_text, test_model_config
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        path = pipeline._save_yaml({"key": "value"}, "task.yaml")
        assert yaml.safe_load(path.read_text()) == {"key": "value"}
        leftovers = [p for p in path.parent.iterdir() if p.suffix == ".tmp"]
        assert leftovers == []

    def test_save_into_subdirectory(self, tmp_path, source_text, test_model_config):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        path = pipeline._save_yaml({"prompt": "p"}, "prompts/item.yaml")
        assert path == pipeline.output_dir / "prompts" / "item.yaml"
        assert yaml.safe_load(path.read_text()) == {"prompt": "p"}

    def test_interrupted_write_leaves_original_intact(
        self, tmp_path, source_text, test_model_config, monkeypatch
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
        path = pipeline._save_yaml({"version": 1}, "task.yaml")

        def exploding_dump(data, stream, **kwargs):
            stream.write("partial: garb")
            raise RuntimeError("disk full")

        monkeypatch.setattr(pipeline_base.yaml, "dump", exploding_dump)
        with pytest.raises(RuntimeError, match="disk full"):
            pipeline._save_yaml({"version": 2}, "task.yaml")

        assert yaml.safe_load(path.read_text()) == {"version": 1}
        leftovers = [p for p in path.parent.iterdir() if p.suffix == ".tmp"]
        assert leftovers == []

    def test_interrupted_first_write_leaves_no_file(
        self, tmp_path, source_text, test_model_config, monkeypatch
    ):
        pipeline = _build_pipeline(tmp_path, source_text, test_model_config)

        def exploding_dump(data, stream, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(pipeline_base.yaml, "dump", exploding_dump)
        with pytest.raises(RuntimeError, match="boom"):
            pipeline._save_yaml({"version": 1}, "task.yaml")

        assert not (pipeline.output_dir / "task.yaml").exists()
