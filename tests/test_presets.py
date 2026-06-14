"""Tests for polyptych.presets."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pytest
import yaml

from polyptych import presets
from polyptych.cli import build_parser


# --- helpers -----------------------------------------------------------------


def _redirect_repo_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Point preset data resolution at a tmp directory for the test."""
    monkeypatch.setattr(presets, "data_path", lambda *parts: root.joinpath(*parts))


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def _ns(**kwargs: Any) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


# --- load_image_preset -------------------------------------------------------


class TestLoadImagePreset:
    def test_loads_known_preset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(
            tmp_path / "image-presets.yaml",
            {"gem": {"provider": "gemini", "size": "1K", "aspect-ratio": "16:9"}},
        )
        _redirect_repo_root(monkeypatch, tmp_path)
        result = presets.load_image_preset("gem")
        assert result == {"provider": "gemini", "size": "1K", "aspect-ratio": "16:9"}

    def test_unknown_name_includes_suggestion(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(tmp_path / "image-presets.yaml", {"openai-low": {}, "gem": {}})
        _redirect_repo_root(monkeypatch, tmp_path)
        with pytest.raises(
            ValueError, match=r"Unknown image preset.*'gemm'.*did you mean 'gem'"
        ):
            presets.load_image_preset("gemm")

    def test_unknown_keys_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(
            tmp_path / "image-presets.yaml",
            {
                "bad": {"provider": "gemini", "concurrent": 10}
            },  # concurrent isn't an image key
        )
        _redirect_repo_root(monkeypatch, tmp_path)
        with pytest.raises(ValueError, match="unknown keys.*concurrent"):
            presets.load_image_preset("bad")

    def test_real_image_presets_yaml_parses(self) -> None:
        # Sanity check on the shipped file.
        result = presets.load_image_preset("gem")
        assert result["provider"] == "gemini"


# --- load_pipeline_preset ----------------------------------------------------


class TestLoadPipelinePreset:
    def test_loads_known_preset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(
            tmp_path / "pipeline-presets.yaml",
            {"slide": {"fast": {"concurrent": 10, "producers": 5}}},
        )
        _redirect_repo_root(monkeypatch, tmp_path)
        result = presets.load_pipeline_preset("slide", "fast")
        assert result == {"concurrent": 10, "producers": 5}

    def test_missing_pipeline_namespace_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(tmp_path / "pipeline-presets.yaml", {})
        _redirect_repo_root(monkeypatch, tmp_path)
        with pytest.raises(ValueError, match="No pipeline presets defined for 'slide'"):
            presets.load_pipeline_preset("slide", "fast")

    def test_unknown_name_includes_suggestion(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(
            tmp_path / "pipeline-presets.yaml",
            {"slide": {"fast": {}, "slow": {}}},
        )
        _redirect_repo_root(monkeypatch, tmp_path)
        with pytest.raises(
            ValueError, match=r"Unknown pipeline preset.*'fastt'.*did you mean 'fast'"
        ):
            presets.load_pipeline_preset("slide", "fastt")

    def test_invalid_keys_for_pipeline(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # critique is valid for infographic but not for slide.
        _write_yaml(
            tmp_path / "pipeline-presets.yaml",
            {"slide": {"weird": {"critique": True}}},
        )
        _redirect_repo_root(monkeypatch, tmp_path)
        with pytest.raises(ValueError, match="unknown keys.*critique"):
            presets.load_pipeline_preset("slide", "weird")


# --- apply_presets -----------------------------------------------------------


class TestApplyPresets:
    def test_image_preset_fills_unset_values(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(
            tmp_path / "image-presets.yaml",
            {"gem": {"provider": "gemini", "size": "1K", "aspect-ratio": "16:9"}},
        )
        _write_yaml(tmp_path / "pipeline-presets.yaml", {})
        _redirect_repo_root(monkeypatch, tmp_path)

        args = _ns(provider=None, size=None, aspect_ratio=None, quality=None)
        presets.apply_presets(
            args, pipeline="slide", image_preset="gem", pipeline_preset=None
        )
        assert args.provider == "gemini"
        assert args.size == "1K"
        assert args.aspect_ratio == "16:9"

    def test_explicit_flag_beats_image_preset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(
            tmp_path / "image-presets.yaml",
            {
                "openai-low": {
                    "provider": "openai",
                    "size": "1536x1024",
                    "quality": "low",
                }
            },
        )
        _write_yaml(tmp_path / "pipeline-presets.yaml", {})
        _redirect_repo_root(monkeypatch, tmp_path)

        # User explicitly passed --quality high.
        args = _ns(provider=None, size=None, aspect_ratio=None, quality="high")
        presets.apply_presets(
            args, pipeline="slide", image_preset="openai-low", pipeline_preset=None
        )
        assert args.quality == "high"  # explicit wins
        assert args.provider == "openai"  # filled from preset
        assert args.size == "1536x1024"  # filled from preset

    def test_pipeline_preset_overrides_image_preset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(
            tmp_path / "image-presets.yaml",
            {"openai-low": {"provider": "openai", "quality": "low"}},
        )
        _write_yaml(
            tmp_path / "pipeline-presets.yaml",
            {"infographic": {"hires": {"critique-rounds": 3}}},
        )
        _redirect_repo_root(monkeypatch, tmp_path)

        args = _ns(
            provider=None,
            size=None,
            aspect_ratio=None,
            quality=None,
            critique_rounds=None,
        )
        presets.apply_presets(
            args,
            pipeline="infographic",
            image_preset="openai-low",
            pipeline_preset="hires",
        )
        assert args.provider == "openai"
        assert args.quality == "low"
        assert args.critique_rounds == 3

    def test_boolean_preset_is_additive_only(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(tmp_path / "image-presets.yaml", {})
        _write_yaml(
            tmp_path / "pipeline-presets.yaml",
            {"infographic": {"crit": {"critique": True}}},
        )
        _redirect_repo_root(monkeypatch, tmp_path)

        # User did not pass --critique (store_true default False); preset enables it.
        args = _ns(provider=None, size=None, aspect_ratio=None, critique=False)
        presets.apply_presets(
            args, pipeline="infographic", image_preset=None, pipeline_preset="crit"
        )
        assert args.critique is True

    def test_from_to_remap_to_start_end(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(tmp_path / "image-presets.yaml", {})
        _write_yaml(
            tmp_path / "pipeline-presets.yaml",
            {"infographic": {"text-only": {"to": "i2"}}},
        )
        _redirect_repo_root(monkeypatch, tmp_path)

        args = _ns(provider=None, size=None, aspect_ratio=None, end=None)
        presets.apply_presets(
            args, pipeline="infographic", image_preset=None, pipeline_preset="text-only"
        )
        assert args.end == "i2"

    def test_final_defaults_fill_after_presets(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(tmp_path / "image-presets.yaml", {})
        _write_yaml(tmp_path / "pipeline-presets.yaml", {})
        _redirect_repo_root(monkeypatch, tmp_path)

        # No presets, no explicit user flags — final defaults must apply.
        args = _ns(provider=None, aspect_ratio=None, size=None, quality=None)
        presets.apply_presets(
            args, pipeline="slide", image_preset=None, pipeline_preset=None
        )
        assert args.provider == "gemini"  # slide default
        assert args.aspect_ratio == "16:9"  # slide default

    def test_real_yaml_files_apply_cleanly(self) -> None:
        # End-to-end against the shipped image-presets.yaml + pipeline-presets.yaml.
        args = _ns(
            provider=None,
            size=None,
            aspect_ratio=None,
            quality=None,
            concurrent=None,
            producers=None,
        )
        presets.apply_presets(
            args, pipeline="slide", image_preset="gem", pipeline_preset="fast"
        )
        assert args.provider == "gemini"
        assert args.size == "1K"
        assert args.aspect_ratio == "16:9"
        assert args.concurrent == 10
        assert args.producers == 5

    def test_size_overrides_pipeline_default_aspect_ratio(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If --size is set but --aspect-ratio is not, derive ratio from size.

        Without this, the pipeline default (e.g. 16:9 for slide) would conflict
        with an explicit portrait size like 1024x1536 and run_config would
        raise.
        """
        _write_yaml(tmp_path / "image-presets.yaml", {})
        _write_yaml(tmp_path / "pipeline-presets.yaml", {})
        _redirect_repo_root(monkeypatch, tmp_path)

        args = _ns(provider=None, size="1024x1536", aspect_ratio=None, quality=None)
        presets.apply_presets(
            args, pipeline="slide", image_preset=None, pipeline_preset=None
        )
        # slide's pipeline default is 16:9, but the size dictates 3:4 here.
        assert args.size == "1024x1536"
        assert args.aspect_ratio == "3:4"


# --- presets vs real argparse parsers (TASK-78 regression) --------------------


def _parse_and_apply(argv: list[str], pipeline: str) -> argparse.Namespace:
    """Parse real CLI argv and run preset resolution, mirroring cli.main()."""
    args = build_parser().parse_args(argv)
    presets.apply_presets(
        args,
        pipeline=pipeline,
        image_preset=getattr(args, "image_preset", None),
        pipeline_preset=getattr(args, "pipeline_preset", None),
    )
    return args


class TestPresetsWithRealParsers:
    """Pipeline presets must take effect against the real argparse defaults.

    Historically the argparse defaults for flags like --critique-rounds and
    --subtype were non-None, so _apply_layer could never tell "user passed the
    default" from "argparse filled it" and preset values were silently
    ignored. The argparse defaults are now None and the documented defaults
    live in presets._PIPELINE_FINAL_DEFAULTS.
    """

    def test_pipeline_preset_beats_argparse_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Use a round count distinct from both the documented default (1) and
        # anything in the shipped YAML, so the preset's effect is unambiguous.
        _write_yaml(
            tmp_path / "pipeline-presets.yaml",
            {"infographic": {"crit4": {"critique-rounds": 4}}},
        )
        _redirect_repo_root(monkeypatch, tmp_path)
        args = _parse_and_apply(
            ["infographic", "src.md", "--pipeline-preset", "crit4"], "infographic"
        )
        assert args.critique_rounds == 4

    def test_explicit_flag_beats_pipeline_preset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(
            tmp_path / "pipeline-presets.yaml",
            {"infographic": {"crit4": {"critique-rounds": 4}}},
        )
        _redirect_repo_root(monkeypatch, tmp_path)
        args = _parse_and_apply(
            [
                "infographic",
                "src.md",
                "--pipeline-preset",
                "crit4",
                "--critique-rounds",
                "1",
            ],
            "infographic",
        )
        assert args.critique_rounds == 1

    def test_no_preset_uses_documented_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _redirect_repo_root(monkeypatch, tmp_path)  # no preset YAMLs at all

        args = _parse_and_apply(["infographic", "src.md"], "infographic")
        assert args.variants == 3
        assert args.critique_rounds == 1
        assert args.start == "auto"
        assert args.end == "images"

        args = _parse_and_apply(["deck", "src.md"], "slide")
        assert args.start == "auto"
        assert args.end == "images"
        assert args.mode == "auto"

    def test_real_infographic_critique_preset_enables_critique(self) -> None:
        """The shipped infographic/critique preset turns the critique loop on."""
        args = _parse_and_apply(
            ["infographic", "src.md", "--pipeline-preset", "critique"], "infographic"
        )
        assert args.critique is True
        # critique-rounds still comes from the documented default.
        assert args.critique_rounds == 1

    def test_real_slide_fast_preset_sets_concurrency(self) -> None:
        # The shipped slide/fast preset sets concurrent+producers.
        args = _parse_and_apply(
            ["deck", "src.md", "--pipeline-preset", "fast"], "slide"
        )
        assert args.concurrent == 10
        assert args.producers == 5


# --- main() validation ordering (TASK-80) -------------------------------------


class TestMainValidationAfterPresets:
    """Concurrency validation must run AFTER preset resolution so that values
    supplied by a pipeline preset are checked like explicit flags."""

    def _run_main(self, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
        from polyptych import cli

        monkeypatch.setattr("sys.argv", ["polyptych", *argv])
        return cli.main()

    def test_preset_producers_without_concurrent_is_rejected(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _write_yaml(
            tmp_path / "pipeline-presets.yaml",
            {"slide": {"prodonly": {"producers": 5}}},
        )
        _redirect_repo_root(monkeypatch, tmp_path)
        rc = self._run_main(
            monkeypatch, ["deck", "src.md", "--pipeline-preset", "prodonly"]
        )
        assert rc == 1
        assert "--producers requires --concurrent" in capsys.readouterr().err

    def test_preset_nonpositive_concurrent_is_rejected(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _write_yaml(
            tmp_path / "pipeline-presets.yaml",
            {"slide": {"bad": {"concurrent": 0}}},
        )
        _redirect_repo_root(monkeypatch, tmp_path)
        rc = self._run_main(monkeypatch, ["deck", "src.md", "--pipeline-preset", "bad"])
        assert rc == 1
        assert "--concurrent must be a positive integer" in capsys.readouterr().err

    def test_preset_with_both_producers_and_concurrent_passes_validation(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from polyptych import cli

        _write_yaml(
            tmp_path / "pipeline-presets.yaml",
            {"slide": {"fastish": {"concurrent": 4, "producers": 2}}},
        )
        _redirect_repo_root(monkeypatch, tmp_path)
        # Stub the handler so main() stops after validation succeeds.
        monkeypatch.setattr(cli, "deck_command", lambda args: 0)
        rc = self._run_main(
            monkeypatch, ["deck", "src.md", "--pipeline-preset", "fastish"]
        )
        assert rc == 0
