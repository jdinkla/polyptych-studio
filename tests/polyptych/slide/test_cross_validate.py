"""Tests for cross-task referential integrity checks (TASK-83).

``polyptych validate`` gains a cross-task pass (per pipeline, slide first)
that runs after schema validation when multiple task files are present.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from polyptych.cross_validate import cross_validate, cross_validate_slide
from polyptych.pipeline_config import TASK_OUTPUT_FILES

from .factories import (
    make_task1_output,
    make_task2_output,
    make_task3_output,
    make_task4_output,
    make_task6_output,
    make_task7_output,
)

SOURCE_5_PARAGRAPHS = "\n\n".join(f"Paragraph {i} text." for i in range(1, 6))


def _write(output_dir: Path, task_name: str, model) -> None:
    path = output_dir / TASK_OUTPUT_FILES[task_name]
    path.write_text(yaml.safe_dump(model.model_dump(), sort_keys=False))


@pytest.fixture
def consistent_dir(tmp_path: Path) -> Path:
    """A slide output dir where all cross-task references line up."""
    (tmp_path / "source.md").write_text(SOURCE_5_PARAGRAPHS)
    _write(tmp_path, "task1", make_task1_output())
    _write(tmp_path, "task2", make_task2_output())
    _write(tmp_path, "task3", make_task3_output(slide_count=3))
    _write(tmp_path, "task4", make_task4_output(slide_count=3))
    _write(tmp_path, "task6", make_task6_output(slide_count=3))
    _write(tmp_path, "task7", make_task7_output(slide_count=3))
    return tmp_path


class TestConsistentDirectory:
    def test_no_findings(self, consistent_dir: Path) -> None:
        assert cross_validate_slide(consistent_dir) == []

    def test_unregistered_pipeline_returns_empty(self, consistent_dir: Path) -> None:
        assert cross_validate("shorts", consistent_dir) == []


class TestDanglingSceneBeatId:
    def test_unknown_beat_id_is_error_naming_id_and_files(
        self, consistent_dir: Path
    ) -> None:
        task4 = make_task4_output(slide_count=3)
        task4.allocations[1].scene_beat_id = "sb_404"
        _write(consistent_dir, "task4", task4)

        findings = cross_validate_slide(consistent_dir)
        errors = [f for f in findings if f.check == "dangling_scene_beat_id"]
        assert len(errors) == 1
        assert errors[0].severity == "error"
        assert "sb_404" in errors[0].message
        assert TASK_OUTPUT_FILES["task4"] in errors[0].message
        assert TASK_OUTPUT_FILES["task2"] in errors[0].message

    def test_known_beat_id_passes(self, consistent_dir: Path) -> None:
        from polyptych.models import SceneBeat

        task2 = make_task2_output(
            scene_beats=[
                SceneBeat(
                    beat_id="sb_001",
                    scene_description="Opening scene",
                    characters_present=["Mina"],
                    location="Office",
                    story_function="hook",
                    key_dialogue=None,
                    source_paragraphs=[1],
                )
            ]
        )
        task4 = make_task4_output(slide_count=3)
        task4.allocations[0].scene_beat_id = "sb_001"
        _write(consistent_dir, "task2", task2)
        _write(consistent_dir, "task4", task4)

        findings = cross_validate_slide(consistent_dir)
        assert [f for f in findings if f.check == "dangling_scene_beat_id"] == []


class TestSlideSetMismatch:
    def test_task7_missing_slide_is_error(self, consistent_dir: Path) -> None:
        _write(consistent_dir, "task7", make_task7_output(slide_count=2))

        findings = cross_validate_slide(consistent_dir)
        errors = [f for f in findings if f.check == "slide_set_mismatch"]
        assert len(errors) == 1
        assert "task7-prompts.yaml" in errors[0].message
        assert "[3]" in errors[0].message  # missing slide 3

    def test_internal_slide_count_mismatch_is_error(self, consistent_dir: Path) -> None:
        task3 = make_task3_output(slide_count=3)
        task3.slide_count = 5  # contradicts the 3-entry sequence
        _write(consistent_dir, "task3", task3)

        findings = cross_validate_slide(consistent_dir)
        assert any(f.check == "slide_count_mismatch" for f in findings)


class TestParagraphRange:
    def test_out_of_range_reference_is_error(self, consistent_dir: Path) -> None:
        task4 = make_task4_output(slide_count=3)
        task4.allocations[0].body_text.source_paragraphs = [1, 400]
        _write(consistent_dir, "task4", task4)

        findings = cross_validate_slide(consistent_dir)
        errors = [f for f in findings if f.check == "paragraph_out_of_range"]
        assert len(errors) == 1
        assert "400" in errors[0].message
        assert "5 paragraphs" in errors[0].message

    def test_task2_section_reference_checked(self, consistent_dir: Path) -> None:
        task2 = make_task2_output()
        task2.structural_analysis.sections[0].paragraph_end = 99
        _write(consistent_dir, "task2", task2)

        findings = cross_validate_slide(consistent_dir)
        assert any(
            f.check == "paragraph_out_of_range" and "99" in f.message for f in findings
        )

    def test_skipped_when_source_missing(self, consistent_dir: Path) -> None:
        (consistent_dir / "source.md").unlink()
        task4 = make_task4_output(slide_count=3)
        task4.allocations[0].body_text.source_paragraphs = [400]
        _write(consistent_dir, "task4", task4)

        findings = cross_validate_slide(consistent_dir)
        assert [f for f in findings if f.check == "paragraph_out_of_range"] == []


class TestSourceSection:
    def test_unknown_section_is_error(self, consistent_dir: Path) -> None:
        task3 = make_task3_output(slide_count=3)
        task3.slide_sequence[2].source_section = "nonexistent"
        _write(consistent_dir, "task3", task3)

        findings = cross_validate_slide(consistent_dir)
        errors = [f for f in findings if f.check == "unknown_source_section"]
        assert len(errors) == 1
        assert "'nonexistent'" in errors[0].message

    def test_section_title_also_accepted(self, consistent_dir: Path) -> None:
        task3 = make_task3_output(slide_count=3)
        task3.slide_sequence[0].source_section = "Opening"  # title of s1
        _write(consistent_dir, "task3", task3)

        findings = cross_validate_slide(consistent_dir)
        assert [f for f in findings if f.check == "unknown_source_section"] == []


class TestArcReferences:
    def test_peak_beyond_sequence_is_error(self, consistent_dir: Path) -> None:
        task3 = make_task3_output(slide_count=3)
        task3.arc_visualization.peaks = [3, 12]
        _write(consistent_dir, "task3", task3)

        findings = cross_validate_slide(consistent_dir)
        errors = [f for f in findings if f.check == "arc_slide_missing"]
        assert len(errors) == 1
        assert "12" in errors[0].message


class TestSoftRules:
    def test_long_headline_is_warning_not_error(self, consistent_dir: Path) -> None:
        task6 = make_task6_output(slide_count=3)
        task6.slides[
            0
        ].content.headline = (
            "This headline rambles on and on far past the documented word limit"
        )
        _write(consistent_dir, "task6", task6)

        findings = cross_validate_slide(consistent_dir)
        warnings = [f for f in findings if f.check == "headline_too_long"]
        assert len(warnings) == 1
        assert warnings[0].severity == "warning"

    def test_long_quote_is_warning(self, consistent_dir: Path) -> None:
        task6 = make_task6_output(slide_count=3)
        task6.slides[1].content.quote = " ".join(["word"] * 30)
        _write(consistent_dir, "task6", task6)

        findings = cross_validate_slide(consistent_dir)
        assert any(
            f.check == "quote_too_long" and f.severity == "warning" for f in findings
        )


class TestValidateCommandIntegration:
    def _run_validate(
        self, monkeypatch: pytest.MonkeyPatch, output_dir: Path
    ) -> tuple[int, dict]:
        import sys

        from polyptych import cli

        monkeypatch.setattr(
            sys, "argv", ["polyptych", "validate", str(output_dir), "--json"]
        )
        import io
        from contextlib import redirect_stdout

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = cli.main()
        return rc, json.loads(buffer.getvalue())

    def test_consistent_dir_exits_zero_with_empty_findings(
        self, consistent_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rc, payload = self._run_validate(monkeypatch, consistent_dir)
        assert rc == 0
        assert payload["cross_task"] == []

    def test_error_finding_fails_and_lands_in_json(
        self, consistent_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        task4 = make_task4_output(slide_count=3)
        task4.allocations[0].scene_beat_id = "sb_404"
        _write(consistent_dir, "task4", task4)

        rc, payload = self._run_validate(monkeypatch, consistent_dir)
        assert rc == 1
        checks = [f["check"] for f in payload["cross_task"]]
        assert "dangling_scene_beat_id" in checks

    def test_warning_alone_does_not_fail(
        self, consistent_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        task6 = make_task6_output(slide_count=3)
        task6.slides[0].content.headline = " ".join(["word"] * 15)
        _write(consistent_dir, "task6", task6)

        rc, payload = self._run_validate(monkeypatch, consistent_dir)
        assert rc == 0
        assert any(f["severity"] == "warning" for f in payload["cross_task"])

    def test_single_task_file_skips_cross_checks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write(tmp_path, "task3", make_task3_output(slide_count=3))

        rc, payload = self._run_validate(monkeypatch, tmp_path)
        assert rc == 0
        assert payload["cross_task"] == []
