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
