"""Frozen dataclass configurations for every pipeline run.

Replaces the 13–30-kwarg surface of each ``run_*_pipeline`` method with a
single typed object. Each subclass exposes ``from_namespace`` to translate an
argparse ``Namespace`` into the right config, and ``_manifest_extras`` to
provide the pipeline-specific fields written into ``manifest.yaml``.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field
from typing import Any


# ---------- base -------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class PipelineRunConfig:
    """Fields shared by every pipeline."""

    provider: str = "gemini"
    size: str | None = None
    aspect_ratio: str = "16:9"
    quality: str | None = None
    image_model: str | None = None
    style_prompt_path: str | None = None
    skip_images: bool = False
    from_step: str = ""
    to_step: str = "images"
    ref_images: list[str] = field(default_factory=list)
    output_format: str | None = None
    output_compression: int | None = None

    def _manifest_extras(self) -> dict[str, Any]:
        """Pipeline-specific keys merged into ``manifest.yaml``."""
        return {"from_step": self.from_step, "to_step": self.to_step}


# ---------- mixins for cluster-shared fields ---------------------------------


@dataclass(frozen=True, kw_only=True)
class _CritiqueOptions:
    skip_critique: bool = False
    critique_rounds: int = 2


@dataclass(frozen=True, kw_only=True)
class _ConcurrencyOptions:
    concurrent: int | None = None
    num_producers: int | None = None
    force: bool = False


# ---------- helpers shared by from_namespace classmethods --------------------


_ASPECT_RATIO_CHOICES: dict[str, float] = {
    "1:1": 1.0,
    "16:9": 16 / 9,
    "4:3": 4 / 3,
    "3:4": 3 / 4,
    "9:16": 9 / 16,
}


def _derive_aspect_ratio_from_size(size: str | None) -> str | None:
    """Pick the closest supported aspect-ratio choice for an explicit WxH size.

    Returns ``None`` if ``size`` is unset or not parseable as ``WxH``.
    """
    if not size or "x" not in size.lower():
        return None
    try:
        w_str, h_str = size.lower().split("x", 1)
        w, h = int(w_str), int(h_str)
    except ValueError:
        return None
    if w <= 0 or h <= 0:
        return None
    ratio = w / h
    return min(
        _ASPECT_RATIO_CHOICES.items(),
        key=lambda kv: abs(math.log(ratio) - math.log(kv[1])),
    )[0]


def _common_image_kwargs(
    args: argparse.Namespace, pipeline_name: str
) -> dict[str, Any]:
    """Read image-related fields shared across every pipeline from argparse.

    If both ``--size`` and ``--aspect-ratio`` are set and the size's implied
    aspect ratio disagrees with ``--aspect-ratio``, this raises ``ValueError``
    rather than silently overriding one of them. Earlier versions printed a
    warning and rewrote ``--aspect-ratio`` to match the size — which masked
    cases like ``--aspect-ratio 9:16 --size 1024x1536`` (1024x1536 is 2:3,
    not 9:16) by quietly producing 3:4-shaped output. After pixbridge's
    rule-based size validation landed, the right move is to surface the
    conflict so the caller fixes it.
    """
    from .cli import _resolve_image_quality, _resolve_ref_images

    size = args.size if args.size else None
    aspect_ratio = args.aspect_ratio
    derived = _derive_aspect_ratio_from_size(size)
    if derived is not None and aspect_ratio is not None and derived != aspect_ratio:
        raise ValueError(
            f"--size {size} implies aspect ratio {derived}, but "
            f"--aspect-ratio {aspect_ratio} was also passed. These are "
            f"inconsistent. Drop one of the two flags, or pick a coherent "
            f"image preset whose size and aspect ratio agree."
        )

    return {
        "provider": args.provider,
        "size": size,
        "aspect_ratio": aspect_ratio,
        "quality": _resolve_image_quality(args, pipeline_name),
        "image_model": getattr(args, "image_model", None),
        "style_prompt_path": args.style,
        "ref_images": _resolve_ref_images(args),
        "output_format": getattr(args, "output_format", None),
        "output_compression": getattr(args, "compression", None),
    }


# ---------- per-pipeline subclasses ------------------------------------------


@dataclass(frozen=True, kw_only=True)
class InfographicRunConfig(PipelineRunConfig, _CritiqueOptions):
    from_step: str = "i0"
    num_variants: int = 3
    skip_critique: bool = True
    critique_rounds: int = 1

    @classmethod
    def from_namespace(
        cls, args: argparse.Namespace, *, from_step: str
    ) -> InfographicRunConfig:
        return cls(
            **_common_image_kwargs(args, "infographic"),
            skip_images=args.skip_images,
            from_step=from_step,
            to_step=args.end,
            num_variants=args.variants,
            skip_critique=not args.critique,
            critique_rounds=args.critique_rounds,
        )

    def _manifest_extras(self) -> dict[str, Any]:
        return {
            "from_step": self.from_step,
            "to_step": self.to_step,
            "num_variants": self.num_variants,
            "critique_rounds": self.critique_rounds if not self.skip_critique else 0,
        }


@dataclass(frozen=True, kw_only=True)
class SlideRunConfig(PipelineRunConfig, _ConcurrencyOptions):
    """Config for the original slide pipeline (``run_from``).

    Uses ``from_step`` / ``to_step`` (renamed from the legacy ``start_step`` /
    ``end_step`` parameters) so the field names align with every other pipeline.
    Manifest writes ``steps: <from>-><to>`` instead of separate fields, matching
    pre-refactor behavior.
    """

    from_step: str = "task1"
    slides: list[int] | None = None
    visuals_only: bool = False
    batch_size: int | None = None
    mode: str = "auto"
    interleave: int | None = None

    @classmethod
    def from_namespace(
        cls,
        args: argparse.Namespace,
        *,
        from_step: str,
        slides: list[int] | None = None,
    ) -> SlideRunConfig:
        return cls(
            **_common_image_kwargs(args, "slide"),
            from_step=from_step,
            to_step=args.end,
            slides=slides,
            visuals_only=args.visuals_only,
            batch_size=args.batch_size,
            mode=getattr(args, "mode", "auto"),
            interleave=args.interleave,
            concurrent=getattr(args, "concurrent", None),
            num_producers=getattr(args, "producers", None),
            force=getattr(args, "force", False),
        )

    def _manifest_extras(self) -> dict[str, Any]:
        return {"steps": f"{self.from_step}->{self.to_step}"}
