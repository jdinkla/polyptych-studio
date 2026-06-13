"""Tests for the typed PipelineRunConfig dataclass family."""

from __future__ import annotations

import argparse

import pytest

from polyptych.run_config import (
    InfographicRunConfig,
    PipelineRunConfig,
    SlideRunConfig,
)


# ---------- defaults ---------------------------------------------------------


def test_base_defaults() -> None:
    cfg = PipelineRunConfig()
    assert cfg.provider == "gemini"
    assert cfg.aspect_ratio == "16:9"
    assert cfg.skip_images is False
    assert cfg.ref_images == []


def test_subclass_defaults() -> None:
    assert InfographicRunConfig().from_step == "i0"
    assert InfographicRunConfig().num_variants == 3
    assert SlideRunConfig().mode == "auto"


def test_frozen() -> None:
    cfg = InfographicRunConfig()
    with pytest.raises(Exception):  # FrozenInstanceError
        cfg.provider = "xai"  # type: ignore[misc]


# ---------- _manifest_extras -------------------------------------------------


def test_manifest_extras_slide_uses_steps_string() -> None:
    cfg = SlideRunConfig(from_step="task1", to_step="task7")
    assert cfg._manifest_extras() == {"steps": "task1->task7"}


def test_manifest_extras_infographic() -> None:
    cfg = InfographicRunConfig(from_step="i0", to_step="images", num_variants=5)
    assert cfg._manifest_extras() == {
        "from_step": "i0",
        "to_step": "images",
        "num_variants": 5,
        "critique_rounds": 0,
    }


def test_manifest_extras_infographic_critique_enabled() -> None:
    cfg = InfographicRunConfig(skip_critique=False, critique_rounds=2)
    assert cfg._manifest_extras()["critique_rounds"] == 2


# ---------- from_namespace ---------------------------------------------------


def _ns(**fields: object) -> argparse.Namespace:
    """Build an argparse.Namespace with sensible defaults that resolvers expect."""
    base = {
        "provider": "gemini",
        "size": None,
        "aspect_ratio": "16:9",
        "quality": None,
        "image_model": None,
        "style": None,
        "skip_images": False,
        "output_format": None,
        "compression": None,
        "ref_image": [],
    }
    base.update(fields)
    return argparse.Namespace(**base)


def test_from_namespace_infographic() -> None:
    args = _ns(variants=4, end="images", critique=False, critique_rounds=1)
    cfg = InfographicRunConfig.from_namespace(args, from_step="i0")
    assert cfg.num_variants == 4
    assert cfg.skip_critique is True
    assert cfg.from_step == "i0"
    assert cfg.to_step == "images"
    assert cfg.provider == "gemini"


def test_from_namespace_slide() -> None:
    args = _ns(
        end="task7",
        visuals_only=False,
        batch_size=10,
        mode="auto",
        interleave=None,
    )
    cfg = SlideRunConfig.from_namespace(args, from_step="task1", slides=[1, 5])
    assert cfg.from_step == "task1"
    assert cfg.to_step == "task7"
    assert cfg.slides == [1, 5]
    assert cfg.batch_size == 10


# ---------- aspect-ratio consistency with explicit size ----------------------
#
# The old silent-rewrite warning is gone: if size and aspect-ratio are both
# set and disagree, run_config raises. Size-aware default-filling lives in
# presets.fill_image_defaults — at the run_config layer, both fields are
# treated as final values.


def test_inconsistent_size_and_aspect_ratio_raises() -> None:
    """1024x1536 is 3:4 (or 2:3); pairing it with --aspect-ratio 16:9 raises."""
    args = _ns(size="1024x1536", variants=3, end="images")
    with pytest.raises(ValueError, match="inconsistent"):
        InfographicRunConfig.from_namespace(args, from_step="i0")


def test_compatible_size_and_aspect_ratio_passes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = _ns(
        size="2560x1440",
        aspect_ratio="16:9",
        variants=3,
        end="images",
        critique=False,
        critique_rounds=1,
    )
    cfg = InfographicRunConfig.from_namespace(args, from_step="i0")
    assert cfg.aspect_ratio == "16:9"
    assert capsys.readouterr().err == ""


def test_no_size_keeps_user_aspect_ratio(
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = _ns(
        size=None,
        aspect_ratio="9:16",
        variants=3,
        end="images",
        critique=False,
        critique_rounds=1,
    )
    cfg = InfographicRunConfig.from_namespace(args, from_step="i0")
    assert cfg.aspect_ratio == "9:16"
    assert capsys.readouterr().err == ""


# ---------- subclass relationships -------------------------------------------


def test_subclasses_inherit_from_base() -> None:
    """All pipeline configs are subtypes of PipelineRunConfig."""
    for cls in (InfographicRunConfig, SlideRunConfig):
        assert issubclass(cls, PipelineRunConfig)
