"""Tests for the fiction character canon (TASK-82).

For fiction sources task2 emits ``character_canon``; task7 embeds each
in-frame character's canonical description verbatim on every slide. The
verbatim guarantee is enforced deterministically by
``apply_character_canon`` / ``inject_character_locks`` — independent of how
well the LLM copied.
"""

from __future__ import annotations

import yaml

from polyptych.models import CharacterSheet, Task2Output
from polyptych.pipeline import SlidePipeline, TASK_OUTPUT_FILES
from polyptych.tasks.task_07_prompts import (
    apply_character_canon,
    format_character_canon,
    inject_character_locks,
)

from ..mock_client import MockTextClient
from .factories import (
    make_image_prompt,
    make_task1_output,
    make_task2_output,
    make_task5_output,
    make_task6_output,
    make_task7_output,
)


def _sheet(name: str = "Mina Harker", **overrides) -> CharacterSheet:
    defaults = dict(
        name=name,
        age="mid 20s",
        face="pale oval face, dark anxious eyes",
        hair="dark brown, pinned back",
        build="slight",
        costume="grey wool traveling coat",
        distinguishing="small silver crucifix",
    )
    defaults.update(overrides)
    return CharacterSheet(**defaults)


class TestCharacterSheet:
    def test_identity_lock_line_is_deterministic(self) -> None:
        sheet = _sheet()
        expected = (
            "Mina Harker: mid 20s; pale oval face, dark anxious eyes; "
            "dark brown, pinned back; slight; grey wool traveling coat; "
            "small silver crucifix"
        )
        assert sheet.identity_lock_line() == expected
        assert sheet.identity_lock_line() == sheet.identity_lock_line()

    def test_distinguishing_is_optional(self) -> None:
        sheet = _sheet(distinguishing=None)
        assert sheet.identity_lock_line().endswith("grey wool traveling coat")

    def test_task2_legacy_yaml_without_canon_validates(self) -> None:
        legacy = make_task2_output().model_dump()
        legacy.pop("character_canon", None)
        assert Task2Output.model_validate(legacy).character_canon is None


class TestInjectCharacterLocks:
    def test_appends_lock_for_matched_character(self) -> None:
        prompt = make_image_prompt(1)
        sheet = _sheet()
        inject_character_locks(prompt, ["Mina Harker (doorway, nervous)"], [sheet])
        assert "CHARACTER IDENTITY LOCK" in prompt.full_prompt
        assert sheet.identity_lock_line() in prompt.full_prompt

    def test_unmatched_characters_do_not_inject(self) -> None:
        prompt = make_image_prompt(1)
        before = prompt.full_prompt
        inject_character_locks(prompt, ["Someone Else"], [_sheet()])
        assert prompt.full_prompt == before

    def test_no_frame_or_no_canon_is_noop(self) -> None:
        prompt = make_image_prompt(1)
        before = prompt.full_prompt
        inject_character_locks(prompt, None, [_sheet()])
        inject_character_locks(prompt, ["Mina Harker"], [])
        assert prompt.full_prompt == before

    def test_idempotent_when_lock_already_present(self) -> None:
        prompt = make_image_prompt(1)
        sheet = _sheet()
        inject_character_locks(prompt, ["Mina Harker"], [sheet])
        once = prompt.full_prompt
        inject_character_locks(prompt, ["Mina Harker"], [sheet])
        assert prompt.full_prompt == once
        assert prompt.full_prompt.count(sheet.identity_lock_line()) == 1

    def test_matching_is_case_insensitive(self) -> None:
        prompt = make_image_prompt(1)
        sheet = _sheet()
        inject_character_locks(prompt, ["MINA HARKER (close-up)"], [sheet])
        assert sheet.identity_lock_line() in prompt.full_prompt


class TestApplyCharacterCanon:
    def test_locks_every_slide_where_character_in_frame(self) -> None:
        sheet = _sheet()
        task6 = make_task6_output(slide_count=3)
        # Character appears on slides 1 and 3 only.
        task6.slides[0].visual.image_spec.characters_in_frame = ["Mina Harker"]
        task6.slides[2].visual.image_spec.characters_in_frame = [
            "Mina Harker (silhouette)"
        ]
        task7 = make_task7_output(slide_count=3)

        apply_character_canon(task7, task6, [sheet])

        line = sheet.identity_lock_line()
        assert line in task7.slide_prompts[0].image_prompt.full_prompt
        assert line not in task7.slide_prompts[1].image_prompt.full_prompt
        assert line in task7.slide_prompts[2].image_prompt.full_prompt
        # Verbatim — the exact same string on both slides.
        assert (
            task7.slide_prompts[0].image_prompt.full_prompt.count(line)
            == task7.slide_prompts[2].image_prompt.full_prompt.count(line)
            == 1
        )

    def test_none_canon_is_noop(self) -> None:
        task6 = make_task6_output(slide_count=1)
        task7 = make_task7_output(slide_count=1)
        before = task7.slide_prompts[0].image_prompt.full_prompt
        apply_character_canon(task7, task6, None)
        assert task7.slide_prompts[0].image_prompt.full_prompt == before


class TestFictionPipelineEndToEnd:
    """YAML-level fiction path: task2 canon flows into task7-prompts.yaml."""

    def test_run_task7_embeds_canon_in_saved_yaml(
        self, slide_pipeline: SlidePipeline, mock_client: MockTextClient
    ) -> None:
        sheet = _sheet()
        slide_pipeline.task1_output = make_task1_output(genre="fiction")
        slide_pipeline.task2_output = make_task2_output(character_canon=[sheet])
        slide_pipeline.task5_output = make_task5_output()
        task6 = make_task6_output(slide_count=2)
        task6.slides[0].visual.image_spec.characters_in_frame = ["Mina Harker"]
        task6.slides[1].visual.image_spec.characters_in_frame = ["Mina Harker (window)"]
        slide_pipeline.task6_output = task6
        mock_client.register_structured("task7", make_task7_output(slide_count=2))

        slide_pipeline.run_task7(provider="gemini")

        saved = yaml.safe_load(
            (slide_pipeline.output_dir / TASK_OUTPUT_FILES["task7"]).read_text()
        )
        line = sheet.identity_lock_line()
        for slide_prompt in saved["slide_prompts"]:
            assert line in slide_prompt["image_prompt"]["full_prompt"]

        # The canon block was injected into the LLM context as well.
        call = mock_client.calls_for("task7")[0]
        assert (
            "Character Canon (fiction — locked identities)"
            in (call["system_instruction"])
        )
        assert line in call["system_instruction"]

    def test_non_fiction_run_is_unchanged(
        self, slide_pipeline: SlidePipeline, mock_client: MockTextClient
    ) -> None:
        slide_pipeline.task1_output = make_task1_output()  # personal_essay
        slide_pipeline.task2_output = make_task2_output()  # no canon
        slide_pipeline.task5_output = make_task5_output()
        slide_pipeline.task6_output = make_task6_output(slide_count=2)
        mock_client.register_structured("task7", make_task7_output(slide_count=2))

        slide_pipeline.run_task7(provider="gemini")

        saved = yaml.safe_load(
            (slide_pipeline.output_dir / TASK_OUTPUT_FILES["task7"]).read_text()
        )
        for slide_prompt in saved["slide_prompts"]:
            assert (
                "CHARACTER IDENTITY LOCK"
                not in (slide_prompt["image_prompt"]["full_prompt"])
            )
        call = mock_client.calls_for("task7")[0]
        assert (
            "Character Canon (fiction — locked identities)"
            not in (call["system_instruction"])
        )

    def test_format_character_canon_lists_all_characters(self) -> None:
        block = format_character_canon([_sheet(), _sheet(name="Mallory")])
        assert "Mina Harker:" in block
        assert "Mallory:" in block
        assert "VERBATIM" in block
