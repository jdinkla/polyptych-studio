"""Tests for deterministic task7 full_prompt assembly and callout baking
(TASK-84).

The model now writes each prompt once (sections only, via the Task7Draft /
ImagePromptDraft schemas); code assembles ``full_prompt`` and injects the
pre-computed text elements — including the previously-missing callout.
"""

from __future__ import annotations

import yaml

from polyptych.models import (
    GenerationNotes,
    ImagePromptDraft,
    ImagePromptSections,
    SlideImagePromptDraft,
    Task7Draft,
)
from polyptych.pipeline import SlidePipeline, TASK_OUTPUT_FILES
from polyptych.tasks.task_07_prompts import (
    DEFAULT_CALLOUT_TREATMENT,
    assemble_full_prompt,
    build_text_elements,
    finalize_draft,
    resolve_callout_treatment,
)

from ..mock_client import MockTextClient
from .factories import (
    make_task1_output,
    make_task5_output,
    make_task6_output,
)


def _sections(**overrides) -> ImagePromptSections:
    defaults = dict(
        goal="Set the scene",
        subject="Rain on a window",
        composition="Rule of thirds",
        spatial_relationships=None,
        setting="Dark office, 1930s",
        lighting="Low key",
        text_elements=None,
        style="Film noir photography",
        fidelity="High detail, film grain",
        consistency="Same palette as slide 1",
    )
    defaults.update(overrides)
    return ImagePromptSections(**defaults)


def _draft(**section_overrides) -> ImagePromptDraft:
    return ImagePromptDraft(
        sections=_sections(**section_overrides),
        generation_notes=GenerationNotes(
            aspect_ratio="16:9",
            negative_prompts=None,
            key_requirements=["rain"],
        ),
    )


class TestAssembleFullPrompt:
    def test_section_order_and_labels(self) -> None:
        prompt = assemble_full_prompt(_sections(text_elements='HEADLINE: "Hi"'))
        blocks = prompt.split("\n\n")
        labels = [b.split(":", 1)[0] for b in blocks]
        assert labels == [
            "GOAL",
            "SUBJECT",
            "COMPOSITION",
            "SETTING",
            "LIGHTING",
            "TEXT ELEMENTS",
            "STYLE",
            "FIDELITY",
            "CONSISTENCY",
        ]

    def test_optional_sections_omitted_when_absent(self) -> None:
        prompt = assemble_full_prompt(_sections())
        assert "SPATIAL RELATIONSHIPS" not in prompt
        assert "TEXT ELEMENTS" not in prompt

    def test_spatial_relationships_included_when_present(self) -> None:
        prompt = assemble_full_prompt(
            _sections(spatial_relationships="desk left of window")
        )
        assert "SPATIAL RELATIONSHIPS: desk left of window" in prompt

    def test_deterministic(self) -> None:
        sections = _sections()
        assert assemble_full_prompt(sections) == assemble_full_prompt(sections)


class TestCalloutInTextElements:
    def test_callout_emitted_with_treatment(self) -> None:
        task6 = make_task6_output(slide_count=1)
        task6.slides[0].content.callout = "73% never returned"
        text = build_text_elements(task6.slides[0], "chalk on blackboard panel")
        assert 'CALLOUT: "73% never returned" - chalk on blackboard panel' in text

    def test_callout_uses_default_treatment_when_none(self) -> None:
        task6 = make_task6_output(slide_count=1)
        task6.slides[0].content.callout = "73% never returned"
        text = build_text_elements(task6.slides[0])
        assert f'CALLOUT: "73% never returned" - {DEFAULT_CALLOUT_TREATMENT}' in text

    def test_no_callout_no_line(self) -> None:
        task6 = make_task6_output(slide_count=1)
        assert "CALLOUT" not in build_text_elements(task6.slides[0])

    def test_resolve_treatment_from_design_system(self) -> None:
        from polyptych.models import SpecialTechnique

        task5 = make_task5_output()
        task5.design_system.special_techniques.append(
            SpecialTechnique(
                technique="callout_treatment",
                when_to_use="Slides with callout field populated",
                visual_spec="Ink wash panel with brush-lettered text",
            )
        )
        assert (
            resolve_callout_treatment(task5)
            == "Ink wash panel with brush-lettered text"
        )

    def test_resolve_treatment_falls_back(self) -> None:
        assert resolve_callout_treatment(make_task5_output()) == (
            DEFAULT_CALLOUT_TREATMENT
        )
        assert resolve_callout_treatment(None) == DEFAULT_CALLOUT_TREATMENT


class TestFinalizeDraft:
    def test_injects_text_elements_and_overrides_model_echo(self) -> None:
        task6 = make_task6_output(slide_count=1)
        draft = _draft(text_elements="MODEL ECHO — should be replaced")
        result = finalize_draft(draft, task6.slides[0], False, None)
        assert result.sections is not None
        assert "MODEL ECHO" not in (result.sections.text_elements or "")
        assert 'HEADLINE: "Slide 1 Headline"' in (result.sections.text_elements or "")
        assert 'HEADLINE: "Slide 1 Headline"' in result.full_prompt

    def test_visuals_only_strips_text_elements(self) -> None:
        task6 = make_task6_output(slide_count=1)
        draft = _draft(text_elements="MODEL ECHO")
        result = finalize_draft(draft, task6.slides[0], True, None)
        assert result.sections is not None
        assert result.sections.text_elements is None
        assert "TEXT ELEMENTS" not in result.full_prompt


class TestRunTask7WithDrafts:
    def test_full_prompt_assembled_and_callout_baked(
        self, slide_pipeline: SlidePipeline, mock_client: MockTextClient
    ) -> None:
        slide_pipeline.task1_output = make_task1_output()
        slide_pipeline.task5_output = make_task5_output()
        task6 = make_task6_output(slide_count=2)
        task6.slides[1].content.callout = "73% never returned"
        slide_pipeline.task6_output = task6

        draft = Task7Draft(
            slide_prompts=[
                SlideImagePromptDraft(slide_number=1, image_prompt=_draft()),
                SlideImagePromptDraft(slide_number=2, image_prompt=_draft()),
            ]
        )
        mock_client.register_structured("task7", draft)

        result = slide_pipeline.run_task7(provider="gemini")

        saved = yaml.safe_load(
            (slide_pipeline.output_dir / TASK_OUTPUT_FILES["task7"]).read_text()
        )
        # full_prompt assembled by code from sections.
        for slide_prompt in saved["slide_prompts"]:
            full = slide_prompt["image_prompt"]["full_prompt"]
            assert full.startswith("GOAL: Set the scene")
            assert "STYLE: Film noir photography" in full
        # Callout baked into slide 2's text elements (and only slide 2's).
        assert "CALLOUT" not in saved["slide_prompts"][0]["image_prompt"]["full_prompt"]
        assert (
            'CALLOUT: "73% never returned"'
            in saved["slide_prompts"][1]["image_prompt"]["full_prompt"]
        )
        # Validates against the persisted schema (full_prompt present).
        assert result.slide_prompts[0].image_prompt.full_prompt
