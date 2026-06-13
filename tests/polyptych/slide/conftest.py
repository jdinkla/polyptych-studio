"""Slide pipeline (Tasks 1-7) test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from polyptych.model_config import ModelConfig
from polyptych.pipeline import SlidePipeline

from ..mock_client import MockTextClient


@pytest.fixture
def slide_pipeline(
    tmp_path: Path,
    source_text: str,
    test_model_config: ModelConfig,
    mock_client: MockTextClient,
) -> SlidePipeline:
    """Construct a SlidePipeline with a mock text client.

    - Source file is written to tmp_path
    - text_provider="gemini" with fallback disabled (lazy init, no API call)
    - pipeline.text_client is replaced with mock_client
    """
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)

    output_dir = tmp_path / "output"

    pipeline = SlidePipeline(
        source_path=source_file,
        output_dir=output_dir,
        model_config=test_model_config,
        text_provider="gemini",
        text_fallback=["none"],
    )
    pipeline.text_client = mock_client

    return pipeline
