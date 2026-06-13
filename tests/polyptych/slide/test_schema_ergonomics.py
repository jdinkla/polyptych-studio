"""Tests for slide schema ergonomics (TASK-86).

Section paragraph membership is a [paragraph_start, paragraph_end] range
(legacy exhaustive lists migrate on load); word_count and
compression_applied are computed in post-processing instead of being
fabricated by the model.
"""

from __future__ import annotations

import pytest

from polyptych.models import SectionAnalysis, Task2Output
from polyptych.pipeline import SlidePipeline

from ..mock_client import MockTextClient
from .factories import (
    make_task1_output,
    make_task2_output,
    make_task3_output,
    make_task4_output,
)


class TestSectionRange:
    def test_canonical_range_fields(self) -> None:
        section = SectionAnalysis(
            id="s1",
            paragraph_start=3,
            paragraph_end=5,
            function="body",
        )
        assert section.paragraphs == [3, 4, 5]
        assert section.word_count is None

    def test_legacy_paragraph_list_migrates(self) -> None:
        section = SectionAnalysis.model_validate(
            {
                "id": "s1",
                "title": None,
                "paragraphs": [3, 4, 5],
                "function": "body",
                "word_count": 312,
            }
        )
        assert section.paragraph_start == 3
        assert section.paragraph_end == 5
        assert section.paragraphs == [3, 4, 5]
        assert section.word_count == 312

    def test_inverted_range_rejected(self) -> None:
        with pytest.raises(ValueError, match="paragraph_end"):
            SectionAnalysis(
                id="s1",
                paragraph_start=5,
                paragraph_end=3,
                function="body",
            )

    def test_legacy_full_task2_yaml_validates(self) -> None:
        legacy = make_task2_output().model_dump()
        for section in legacy["structural_analysis"]["sections"]:
            start = section.pop("paragraph_start")
            end = section.pop("paragraph_end")
            section["paragraphs"] = list(range(start, end + 1))
            section["word_count"] = 100
        migrated = Task2Output.model_validate(legacy)
        assert migrated.structural_analysis.sections[0].paragraph_start == 1


class TestComputedFields:
    SOURCE = "\n\n".join(
        f"Paragraph {i} has exactly six words here." for i in range(1, 6)
    )

    def test_task2_word_count_computed_from_source(
        self, slide_pipeline: SlidePipeline, mock_client: MockTextClient
    ) -> None:
        from polyptych.tasks import run_task_02

        llm_output = make_task2_output()
        # The model fabricates counts — post-processing must overwrite them.
        llm_output.structural_analysis.sections[0].word_count = 9999
        mock_client.register_structured("task2", llm_output)

        result = run_task_02(
            source_essay=self.SOURCE,
            task1_output=make_task1_output(),
            client=mock_client,
            model="test-model",
        )

        # s1 covers paragraphs 1-2 → 2 paragraphs x 7 words.
        assert result.structural_analysis.sections[0].word_count == 14
        # s3 covers paragraph 5 only.
        assert result.structural_analysis.sections[2].word_count == 7

    def test_task4_compression_computed(
        self, slide_pipeline: SlidePipeline, mock_client: MockTextClient
    ) -> None:
        from polyptych.tasks import run_task_04

        llm_output = make_task4_output(slide_count=1)
        llm_output.allocations[0].body_text.source_paragraphs = [1, 2]
        llm_output.allocations[
            0
        ].body_text.summary = "Seven word summary right here ok done"
        llm_output.allocations[0].body_text.compression_applied = 123.0  # fabricated
        mock_client.register_structured("task4", llm_output)

        result = run_task_04(
            source_essay=self.SOURCE,
            task1_output=make_task1_output(),
            task2_output=make_task2_output(),
            task3_output=make_task3_output(slide_count=1),
            client=mock_client,
            model="test-model",
        )

        # 14 source words / 7 summary words = 2.0
        assert result.allocations[0].body_text.compression_applied == 2.0
