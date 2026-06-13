"""Tests for task7 prompt-provider recording and the image-time mismatch
warning (TASK-81).

Task7 bakes provider-specific guidelines into the generated prompts, but the
image provider can differ on resume (``--from images`` with another
``--provider`` / ``--image-preset``). The pipeline records which provider the
prompts were tuned for in ``Task7Output.prompt_provider`` and warns when the
image run uses a different one.
"""

from __future__ import annotations

import yaml

from polyptych.models import Task7Output
from polyptych.pipeline import SlidePipeline, TASK_OUTPUT_FILES

from ..mock_client import MockImageClient, MockTextClient
from .factories import (
    make_task1_output,
    make_task5_output,
    make_task6_output,
    make_task7_output,
)


def _prepare_for_task7(pipeline: SlidePipeline, mock_client: MockTextClient) -> None:
    pipeline.task1_output = make_task1_output()
    pipeline.task5_output = make_task5_output()
    pipeline.task6_output = make_task6_output(slide_count=2)
    mock_client.register_structured("task7", make_task7_output(slide_count=2))


class TestPromptProviderRecording:
    def test_run_task7_stamps_provider_into_yaml(
        self, slide_pipeline: SlidePipeline, mock_client: MockTextClient
    ) -> None:
        _prepare_for_task7(slide_pipeline, mock_client)

        result = slide_pipeline.run_task7(provider="openai")

        assert result.prompt_provider == "openai"
        saved = yaml.safe_load(
            (slide_pipeline.output_dir / TASK_OUTPUT_FILES["task7"]).read_text()
        )
        assert saved["prompt_provider"] == "openai"

    def test_stamp_overwrites_llm_supplied_value(
        self, slide_pipeline: SlidePipeline, mock_client: MockTextClient
    ) -> None:
        slide_pipeline.task1_output = make_task1_output()
        slide_pipeline.task5_output = make_task5_output()
        slide_pipeline.task6_output = make_task6_output(slide_count=2)
        # The LLM is never trusted with this field — even if it fills it.
        llm_output = make_task7_output(slide_count=2)
        llm_output.prompt_provider = "made-up-by-llm"
        mock_client.register_structured("task7", llm_output)

        result = slide_pipeline.run_task7(provider="gemini")

        assert result.prompt_provider == "gemini"

    def test_legacy_yaml_without_field_validates_to_none(self) -> None:
        legacy = {"slide_prompts": []}
        assert Task7Output.model_validate(legacy).prompt_provider is None


class TestMismatchWarning:
    def _run_images(self, pipeline: SlidePipeline, provider: str) -> None:
        from unittest.mock import patch

        with patch.object(
            pipeline, "_make_image_client", return_value=MockImageClient()
        ):
            pipeline.run_images(provider=provider)

    def test_warns_when_image_provider_differs(
        self, slide_pipeline: SlidePipeline, capsys
    ) -> None:
        slide_pipeline.task7_output = make_task7_output(
            slide_count=1, prompt_provider="gemini"
        )
        self._run_images(slide_pipeline, provider="openai")

        out = capsys.readouterr().out
        assert "WARNING" in out
        assert "'gemini'" in out
        assert "'openai'" in out

    def test_silent_when_providers_match(
        self, slide_pipeline: SlidePipeline, capsys
    ) -> None:
        slide_pipeline.task7_output = make_task7_output(
            slide_count=1, prompt_provider="openai"
        )
        self._run_images(slide_pipeline, provider="openai")

        assert "WARNING: task7 prompts were tuned" not in capsys.readouterr().out

    def test_silent_for_legacy_outputs_without_record(
        self, slide_pipeline: SlidePipeline, capsys
    ) -> None:
        slide_pipeline.task7_output = make_task7_output(slide_count=1)
        assert slide_pipeline.task7_output.prompt_provider is None
        self._run_images(slide_pipeline, provider="openai")

        assert "WARNING: task7 prompts were tuned" not in capsys.readouterr().out
