"""Tests for pipeline resume logic.

Covers find_resume_step (pipeline.py) and resolve_from_step (cli.py) since
they form a single decision flow: CLI passes 'auto' / explicit / --force
through resolve_from_step, which delegates to find_resume_step for the
actual filesystem walk.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from polyptych.cli import resolve_from_step
from polyptych.pipeline import find_resume_step


# A tiny schema used to force validation on one of the steps.
class _Output(BaseModel):
    name: str
    value: int


# Four-step fixture: s1, s2, and s3 are tracked; "images" is untracked.
STEPS = ["s1", "s2", "s3", "images"]
OUTPUT_FILES = {
    "s1": "s1.yaml",
    "s2": "s2.yaml",
    "s3": "s3.yaml",
}
MODELS = {"s2": _Output}  # Only s2 has a strict schema.


def _write(path: Path, data: object) -> None:
    path.write_text(yaml.safe_dump(data))


# ---------------------------------------------------------------------------
# find_resume_step
# ---------------------------------------------------------------------------


class TestFindResumeStep:
    def test_empty_dir_returns_first_step(self, tmp_path):
        assert find_resume_step(tmp_path, STEPS, OUTPUT_FILES, MODELS) == "s1"

    def test_all_valid_returns_none(self, tmp_path):
        _write(tmp_path / "s1.yaml", {"anything": 1})
        _write(tmp_path / "s2.yaml", {"name": "x", "value": 7})
        _write(tmp_path / "s3.yaml", {"ok": True})
        assert find_resume_step(tmp_path, STEPS, OUTPUT_FILES, MODELS) is None

    def test_missing_middle_file_resumes_from_gap(self, tmp_path):
        _write(tmp_path / "s1.yaml", {"a": 1})
        # s2 missing
        _write(tmp_path / "s3.yaml", {"c": 3})
        assert find_resume_step(tmp_path, STEPS, OUTPUT_FILES, MODELS) == "s2"

    def test_empty_file_treated_as_missing(self, tmp_path):
        _write(tmp_path / "s1.yaml", {"a": 1})
        (tmp_path / "s2.yaml").write_text("")
        assert find_resume_step(tmp_path, STEPS, OUTPUT_FILES, MODELS) == "s2"

    def test_yaml_parsing_to_none_treated_as_invalid(self, tmp_path):
        _write(tmp_path / "s1.yaml", {"a": 1})
        # Comment-only YAML parses to None.
        (tmp_path / "s2.yaml").write_text("# just a comment\n")
        assert find_resume_step(tmp_path, STEPS, OUTPUT_FILES, MODELS) == "s2"

    def test_malformed_yaml_treated_as_invalid(self, tmp_path):
        _write(tmp_path / "s1.yaml", {"a": 1})
        (tmp_path / "s2.yaml").write_text("not: valid: yaml: [nested wrong")
        assert find_resume_step(tmp_path, STEPS, OUTPUT_FILES, MODELS) == "s2"

    def test_schema_validation_failure_triggers_resume(self, tmp_path):
        _write(tmp_path / "s1.yaml", {"a": 1})
        # s2 requires {name: str, value: int}; we give it wrong types.
        _write(tmp_path / "s2.yaml", {"name": "x", "value": "not-an-int"})
        assert find_resume_step(tmp_path, STEPS, OUTPUT_FILES, MODELS) == "s2"

    def test_untracked_step_stops_walk(self, tmp_path):
        # All tracked steps exist. The "images" step has no entry in
        # output_files, so the walk should return None (all valid).
        _write(tmp_path / "s1.yaml", {"a": 1})
        _write(tmp_path / "s2.yaml", {"name": "x", "value": 7})
        _write(tmp_path / "s3.yaml", {"c": 3})
        assert find_resume_step(tmp_path, STEPS, OUTPUT_FILES, MODELS) is None

    def test_step_without_model_skips_schema_check(self, tmp_path):
        # s1 has no entry in MODELS — any valid YAML should satisfy it.
        _write(tmp_path / "s1.yaml", {"totally": ["different", "shape"]})
        _write(tmp_path / "s2.yaml", {"name": "x", "value": 7})
        _write(tmp_path / "s3.yaml", {"c": 3})
        assert find_resume_step(tmp_path, STEPS, OUTPUT_FILES, MODELS) is None

    def test_first_step_missing_returns_first_step(self, tmp_path):
        # Even if later files exist, a missing first step takes priority.
        _write(tmp_path / "s2.yaml", {"name": "x", "value": 7})
        _write(tmp_path / "s3.yaml", {"c": 3})
        assert find_resume_step(tmp_path, STEPS, OUTPUT_FILES, MODELS) == "s1"


# ---------------------------------------------------------------------------
# resolve_from_step
# ---------------------------------------------------------------------------


class TestResolveFromStep:
    def test_explicit_step_passes_through(self, tmp_path):
        # Non-'auto' values are returned unchanged, filesystem is not read.
        assert (
            resolve_from_step("s2", tmp_path, STEPS, OUTPUT_FILES, MODELS)
            == "s2"
        )

    def test_force_starts_at_first_step(self, tmp_path):
        # Even when all outputs exist, --force should restart from s1.
        _write(tmp_path / "s1.yaml", {"a": 1})
        _write(tmp_path / "s2.yaml", {"name": "x", "value": 7})
        _write(tmp_path / "s3.yaml", {"c": 3})
        assert (
            resolve_from_step(
                "auto", tmp_path, STEPS, OUTPUT_FILES, MODELS, force=True,
            )
            == "s1"
        )

    def test_auto_empty_dir_resumes_from_first_step(self, tmp_path, capsys):
        assert (
            resolve_from_step("auto", tmp_path, STEPS, OUTPUT_FILES, MODELS)
            == "s1"
        )
        assert "Starting from scratch" in capsys.readouterr().out

    def test_auto_partial_resumes_from_first_gap(self, tmp_path, capsys):
        _write(tmp_path / "s1.yaml", {"a": 1})
        # s2 missing — resume there, announce "valid through 's1'"
        resolved = resolve_from_step(
            "auto", tmp_path, STEPS, OUTPUT_FILES, MODELS,
        )
        assert resolved == "s2"
        assert "valid through 's1'" in capsys.readouterr().out

    def test_auto_all_valid_jumps_to_first_untracked_step(self, tmp_path):
        _write(tmp_path / "s1.yaml", {"a": 1})
        _write(tmp_path / "s2.yaml", {"name": "x", "value": 7})
        _write(tmp_path / "s3.yaml", {"c": 3})
        # All tracked steps valid → jump to the first untracked step ("images").
        assert (
            resolve_from_step("auto", tmp_path, STEPS, OUTPUT_FILES, MODELS)
            == "images"
        )

    def test_auto_falls_back_to_last_step_when_no_untracked(self, tmp_path):
        # Edge case: all steps are tracked. When all are valid, resolve_from_step
        # jumps to the last step (steps[-1]) since there's nothing untracked.
        all_tracked_files = {"s1": "s1.yaml", "s2": "s2.yaml", "s3": "s3.yaml"}
        all_tracked_steps = ["s1", "s2", "s3"]
        _write(tmp_path / "s1.yaml", {"a": 1})
        _write(tmp_path / "s2.yaml", {"name": "x", "value": 7})
        _write(tmp_path / "s3.yaml", {"c": 3})
        assert (
            resolve_from_step(
                "auto", tmp_path, all_tracked_steps, all_tracked_files, MODELS,
            )
            == "s3"
        )
