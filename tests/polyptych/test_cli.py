"""Smoke tests for polyptych.cli.

Covers argument parsing, selection parsers, and the missing-source-file
error path for every subcommand. The heavy happy-path work lives inside
SlidePipeline, which has its own tests — here we only verify that the
CLI layer routes correctly and produces the right exit codes.
"""

from __future__ import annotations

import argparse
from unittest.mock import patch

import pytest

from polyptych.cli import (
    _resolve_image_quality,
    _resolve_ref_images,
    _run_pipeline_command,
    clean_source_command,
    deck_command,
    infographic_command,
    main,
    parse_scene_selection,
    parse_slide_selection,
    validate_command,
)


# ---------------------------------------------------------------------------
# Selection parsers
# ---------------------------------------------------------------------------


class TestParseSlideSelection:
    @pytest.mark.parametrize(
        "selection,expected",
        [
            ("1", [1]),
            ("1,3,5", [1, 3, 5]),
            ("1-3", [1, 2, 3]),
            ("1-3,5,8-10", [1, 2, 3, 5, 8, 9, 10]),
            ("5, 3, 1", [1, 3, 5]),
            ("1,1,1", [1]),
            ("2-4,3-5", [2, 3, 4, 5]),
            (" 1 - 3 ", [1, 2, 3]),
        ],
    )
    def test_parses_and_dedups(self, selection, expected):
        assert parse_slide_selection(selection) == expected


class TestParseSceneSelection:
    # Currently the scene parser has identical semantics to slide — verify
    # they agree so a divergence is caught.
    @pytest.mark.parametrize(
        "selection",
        ["1", "1,3,5", "1-3", "1-3,5,8-10", "5,3,1", "2-4,3-5"],
    )
    def test_matches_slide_parser(self, selection):
        assert parse_scene_selection(selection) == parse_slide_selection(selection)


# ---------------------------------------------------------------------------
# Subcommand smoke tests: missing source file → 1, prints to stderr
# ---------------------------------------------------------------------------


def _pipeline_args(source_file: str, output_dir: str | None = None):
    """Baseline Namespace that satisfies every pipeline/narrative/etc. command."""
    return argparse.Namespace(
        source_file=source_file,
        output_dir=output_dir,
        model=None,
        text_provider="gemini",
        text_fallback=None,
        image_model=None,
        start="auto",
        end=None,
        provider="gemini",
        size=None,
        aspect_ratio="16:9",
        quality=None,
        slides=None,
        visuals_only=False,
        style=None,
        batch_size=1,
        mode="auto",
        interleave=False,
        concurrent=None,
        producers=None,
        force=False,
    )


class TestSubcommandMissingSource:
    """Every pipeline subcommand should exit 1 and report the missing source."""

    @pytest.mark.parametrize(
        "handler",
        [
            deck_command,
            infographic_command,
        ],
    )
    def test_missing_source_returns_1(self, handler, tmp_path, capsys):
        args = _pipeline_args(
            source_file=str(tmp_path / "does-not-exist.md"),
            output_dir=str(tmp_path / "out"),
        )
        # Some handlers read command-specific fields not on the baseline —
        # setattr sensible defaults so argparse.Namespace access doesn't AttributeError.
        for extra in (
            "subtype",
            "all_shorts",
            "scenes",
            "characters",
            "locations",
            "items",
        ):
            if not hasattr(args, extra):
                setattr(args, extra, None)
        code = handler(args)
        assert code == 1
        err = capsys.readouterr().err
        assert "not found" in err.lower()


class TestValidateCommand:
    def test_missing_output_dir_returns_1(self, tmp_path, capsys):
        args = argparse.Namespace(
            output_dir=str(tmp_path / "nope"),
            task_name=None,
            json_output=False,
        )
        code = validate_command(args)
        assert code == 1
        assert "Directory not found" in capsys.readouterr().err

    def test_empty_output_dir_returns_0_with_message(self, tmp_path, capsys):
        # Directory exists but no task outputs → reports "No task outputs"
        args = argparse.Namespace(
            output_dir=str(tmp_path),
            task_name=None,
            json_output=False,
        )
        code = validate_command(args)
        assert code == 0
        assert "No task outputs found" in capsys.readouterr().out

    def test_unknown_task_name_returns_1(self, tmp_path, capsys):
        args = argparse.Namespace(
            output_dir=str(tmp_path),
            task_name="not-a-real-task",
            json_output=False,
        )
        code = validate_command(args)
        assert code == 1
        assert "Unknown task" in capsys.readouterr().err

    def test_empty_dir_json_output(self, tmp_path, capsys):
        args = argparse.Namespace(
            output_dir=str(tmp_path),
            task_name=None,
            json_output=True,
        )
        code = validate_command(args)
        assert code == 0
        # JSON structure when nothing present
        out = capsys.readouterr().out
        assert '"pipeline": null' in out
        assert '"tasks": []' in out


class TestCleanSourceCommand:
    def test_missing_input_returns_1(self, tmp_path, capsys):
        args = argparse.Namespace(
            input_file=str(tmp_path / "nope.md"),
            output=None,
            dry_run=False,
            keep_toc=False,
            keep_images=False,
            keep_footnotes=False,
            keep_page_numbers=False,
            keep_escapes=False,
        )
        code = clean_source_command(args)
        assert code == 1
        assert "File not found" in capsys.readouterr().err

    def test_dry_run_returns_0_and_reports(self, tmp_path, capsys):
        input_file = tmp_path / "raw.md"
        input_file.write_text("# Essay\n\nSome body text.\n\n1\n\nMore body.\n")
        args = argparse.Namespace(
            input_file=str(input_file),
            output=None,
            dry_run=True,
            keep_toc=False,
            keep_images=False,
            keep_footnotes=False,
            keep_page_numbers=False,
            keep_escapes=False,
        )
        code = clean_source_command(args)
        assert code == 0
        out = capsys.readouterr().out
        assert "Cleaning report" in out
        # Output file should NOT exist — dry run is read-only.
        assert not (tmp_path / "raw.cleaned.md").exists()


# ---------------------------------------------------------------------------
# main() routing via sys.argv patching
# ---------------------------------------------------------------------------


class TestMainRouting:
    def test_no_command_prints_help(self, capsys):
        with patch("sys.argv", ["polyptych"]):
            code = main()
        assert code == 0
        assert "Available commands" in capsys.readouterr().out

    def test_help_flag_exits_0(self, capsys):
        with patch("sys.argv", ["polyptych", "--help"]):
            with pytest.raises(SystemExit) as excinfo:
                main()
        assert excinfo.value.code == 0

    def test_unknown_subcommand_exits_nonzero(self, capsys):
        with patch("sys.argv", ["polyptych", "not-a-command"]):
            with pytest.raises(SystemExit) as excinfo:
                main()
        assert excinfo.value.code != 0

    def test_validate_routes_to_handler(self, tmp_path):
        # Point at a nonexistent dir → validate_command returns 1.
        with patch("sys.argv", ["polyptych", "validate", str(tmp_path / "nope")]):
            code = main()
        assert code == 1

    def test_clean_source_routes_to_handler(self, tmp_path):
        with patch(
            "sys.argv",
            ["polyptych", "clean-source", str(tmp_path / "nope.md")],
        ):
            code = main()
        assert code == 1

    def test_deck_routes_to_deck_command(self, tmp_path, capsys):
        # Missing source → deck_command returns 1. No deprecation notice.
        with patch(
            "sys.argv",
            ["polyptych", "deck", str(tmp_path / "nope.md")],
        ):
            code = main()
        assert code == 1
        err = capsys.readouterr().err
        assert "deprecated" not in err

    def test_pipeline_alias_is_removed(self, tmp_path):
        # `pipeline` alias has been removed; argparse should reject it with SystemExit.
        with patch(
            "sys.argv",
            ["polyptych", "pipeline", str(tmp_path / "nope.md")],
        ):
            with pytest.raises(SystemExit) as excinfo:
                main()
        assert excinfo.value.code != 0


# ---------------------------------------------------------------------------
# _resolve_image_quality
# ---------------------------------------------------------------------------


def _ns(**kwargs) -> argparse.Namespace:
    """Build a namespace with arbitrary attributes for helper tests."""
    return argparse.Namespace(**kwargs)


class TestResolveImageQuality:
    def test_explicit_quality_wins_over_default(self):
        args = _ns(quality="low", provider="openai")
        assert _resolve_image_quality(args, "slide") == "low"

    def test_openai_text_heavy_defaults_to_high(self):
        args = _ns(quality=None, provider="openai")
        assert _resolve_image_quality(args, "slide") == "high"
        assert _resolve_image_quality(args, "infographic") == "high"

    def test_non_openai_provider_returns_none(self):
        args = _ns(quality=None, provider="gemini")
        assert _resolve_image_quality(args, "slide") is None

    def test_unknown_pipeline_returns_none(self):
        args = _ns(quality=None, provider="openai")
        assert _resolve_image_quality(args, "unknown-pipeline") is None

    def test_missing_quality_attr_treated_as_none(self):
        args = _ns(provider="openai")  # no .quality
        assert _resolve_image_quality(args, "slide") == "high"


# ---------------------------------------------------------------------------
# _resolve_ref_images
# ---------------------------------------------------------------------------


class TestResolveRefImages:
    def test_returns_empty_when_nothing_set(self):
        args = _ns(style=None, ref_image=None)
        assert _resolve_ref_images(args) == []

    def test_returns_user_refs_in_order(self):
        args = _ns(style=None, ref_image=["a.png", "b.png", "c.png"])
        assert _resolve_ref_images(args) == ["a.png", "b.png", "c.png"]

    def test_style_exemplar_first_then_user_refs(self, tmp_path):
        style_md = tmp_path / "noir.md"
        style_md.write_text("# Noir")
        png = tmp_path / "noir.png"
        png.write_bytes(b"p")
        args = _ns(style=str(style_md), ref_image=["a.png", "b.png"])
        assert _resolve_ref_images(args) == [str(png), "a.png", "b.png"]

    def test_style_without_exemplar_is_silently_ignored(self, tmp_path):
        style_md = tmp_path / "noir.md"
        style_md.write_text("# Noir")  # no companion image
        args = _ns(style=str(style_md), ref_image=["a.png"])
        assert _resolve_ref_images(args) == ["a.png"]

    def test_missing_attrs_treated_as_none(self):
        # CLI subparsers all add these flags, but be defensive against future
        # callers building a custom Namespace.
        args = argparse.Namespace()
        assert _resolve_ref_images(args) == []


# ---------------------------------------------------------------------------
# Exception logging: unexpected errors must be logged with a stack trace
# ---------------------------------------------------------------------------


def _base_pipeline_args(source_file: str, output_dir: str) -> argparse.Namespace:
    """Minimal Namespace that satisfies _run_pipeline_command."""
    return argparse.Namespace(
        source_file=source_file,
        output_dir=output_dir,
        model=None,
        text_provider="gemini",
        text_fallback=None,
        image_model=None,
        start="auto",
        end=None,
        provider="gemini",
        size=None,
        aspect_ratio="16:9",
        quality=None,
        slides=None,
        visuals_only=False,
        style=None,
        batch_size=1,
        mode="auto",
        interleave=False,
        concurrent=None,
        producers=None,
        force=False,
    )


@pytest.fixture
def propagate_polyptych_logs(monkeypatch):
    """Re-enable propagation on the 'polyptych' logger for caplog.

    Earlier tests that go through main() call configure_logging(), which sets
    propagate=False on the package logger; caplog's root handler would then
    never see records from polyptych.cli.
    """
    import logging

    monkeypatch.setattr(logging.getLogger("polyptych"), "propagate", True)


class TestRunPipelineCommandExceptionLogging:
    """The bare except-Exception handler in _run_pipeline_command must log with
    a full stack trace while still printing the user-facing message to stderr."""

    @pytest.fixture(autouse=True)
    def _propagate(self, propagate_polyptych_logs):
        pass

    def test_unexpected_exception_is_logged_with_traceback(
        self, tmp_path, capsys, caplog
    ):
        import logging

        from polyptych.pipeline import ALL_STEPS, TASK_MODELS, TASK_OUTPUT_FILES
        from polyptych.run_config import SlideRunConfig

        source = tmp_path / "essay.md"
        source.write_text("# Essay\n\nbody")
        args = _base_pipeline_args(str(source), str(tmp_path / "out"))

        boom = RuntimeError("something truly unexpected")

        with caplog.at_level(logging.ERROR, logger="polyptych.cli"):
            with patch(
                "polyptych.cli.SlidePipeline",
                side_effect=boom,
            ):
                code = _run_pipeline_command(
                    args,
                    default_output_dir="out",
                    steps=ALL_STEPS,
                    output_files=TASK_OUTPUT_FILES,
                    models=TASK_MODELS,
                    make_run_config=SlideRunConfig.from_namespace,
                    run_method="run_slide_pipeline",
                )

        assert code == 1
        err = capsys.readouterr().err
        assert "something truly unexpected" in err

        # The exception must have been logged (caplog captures it).
        assert any(
            "unexpected" in r.message.lower() and r.exc_info is not None
            for r in caplog.records
        )

    def test_transient_provider_error_not_logged_as_exception(
        self, tmp_path, capsys, caplog
    ):
        """TransientProviderError is an expected failure — no stack trace needed."""
        import logging

        from polyptych.pipeline import ALL_STEPS, TASK_MODELS, TASK_OUTPUT_FILES
        from polyptych.providers.base import TransientProviderError
        from polyptych.run_config import SlideRunConfig

        source = tmp_path / "essay.md"
        source.write_text("# Essay\n\nbody")
        args = _base_pipeline_args(str(source), str(tmp_path / "out"))

        with caplog.at_level(logging.WARNING, logger="polyptych.cli"):
            with patch(
                "polyptych.cli.SlidePipeline",
                side_effect=TransientProviderError("rate limited"),
            ):
                code = _run_pipeline_command(
                    args,
                    default_output_dir="out",
                    steps=ALL_STEPS,
                    output_files=TASK_OUTPUT_FILES,
                    models=TASK_MODELS,
                    make_run_config=SlideRunConfig.from_namespace,
                    run_method="run_slide_pipeline",
                )

        assert code == 1
        err = capsys.readouterr().err
        assert "rate limited" in err
        # No exception record logged for an expected failure type.
        assert not any(r.exc_info is not None for r in caplog.records)


# ---------------------------------------------------------------------------
# Aggregated image-failure reporting (exit code + end-of-run summary)
# ---------------------------------------------------------------------------


class TestImageFailureAggregation:
    def _run(self, tmp_path, monkeypatch, failures):
        """Drive _run_pipeline_command with a stub pipeline seeded with failures."""
        from polyptych.image_batch import ImageFailure

        source = tmp_path / "source.md"
        source.write_text("essay text")
        args = _pipeline_args(str(source), str(tmp_path / "out"))
        args.start = "task1"

        class StubPipeline:
            def __init__(self, **kwargs):
                self.image_failures = []

            def run(self, config) -> None:
                self.image_failures.extend(ImageFailure(*f) for f in failures)

        monkeypatch.setattr("polyptych.cli.SlidePipeline", StubPipeline)
        return _run_pipeline_command(
            args,
            default_output_dir=tmp_path / "out",
            steps=["task1"],
            output_files={},
            models={},
            make_run_config=lambda args, from_step, **kw: None,
            run_method="run",
        )

    def test_all_images_succeed_exits_0(self, tmp_path, monkeypatch, capsys):
        code = self._run(tmp_path, monkeypatch, failures=[])
        assert code == 0
        assert "failed to" not in capsys.readouterr().err

    def test_partial_failure_exits_1_with_summary(self, tmp_path, monkeypatch, capsys):
        code = self._run(
            tmp_path,
            monkeypatch,
            failures=[
                ("slide", 2, "RuntimeError: provider 500"),
                ("slide", 5, "TimeoutError: timed out"),
            ],
        )
        assert code == 1
        err = capsys.readouterr().err
        assert "2 image(s) failed" in err
        assert "Slide 2: RuntimeError: provider 500" in err
        assert "Slide 5: TimeoutError: timed out" in err
        assert "Re-run the same command" in err
