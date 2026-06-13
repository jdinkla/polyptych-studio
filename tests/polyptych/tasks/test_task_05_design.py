"""Tests for Task 5 (visual design specification) — style-preset awareness."""

from __future__ import annotations

from polyptych.tasks.task_05_design import run_task_05

from tests.polyptych.slide.factories import (
    make_task1_output,
    make_task2_output,
    make_task4_output,
    make_task5_output,
)


def _run(mock_client, style_prompt: str | None = None):
    mock_client.register_structured("task5", make_task5_output())
    run_task_05(
        task1_output=make_task1_output(),
        task2_output=make_task2_output(),
        task4_output=make_task4_output(),
        client=mock_client,  # type: ignore[arg-type]
        model="test-model",
        style_prompt=style_prompt,
    )
    return mock_client.last_call("task5")


class TestRunTask05StylePrompt:
    def test_style_section_appended_when_provided(self, mock_client):
        call = _run(mock_client, style_prompt="Stark noir black-and-white ink style.")
        assert "## Style Transfer Preset" in call["prompt"]
        assert "Stark noir black-and-white ink style." in call["prompt"]

    def test_no_style_section_when_omitted(self, mock_client):
        call = _run(mock_client, style_prompt=None)
        assert "Style Transfer Preset" not in call["prompt"]
