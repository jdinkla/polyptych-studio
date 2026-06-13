"""Stacked image and pipeline presets for the polyptych CLI.

Presets bundle commonly-used flag combinations into named entries in two YAML
files at the repo root:

* ``image-presets.yaml`` — global: provider/size/aspect-ratio/quality/etc.
* ``pipeline-presets.yaml`` — per-pipeline: concurrency, --skip-refs, --subtype, etc.

The CLI exposes ``--image-preset NAME`` and ``--pipeline-preset NAME`` on every
image-producing subcommand. ``apply_presets`` fills the argparse Namespace
with values from the named presets, leaving any flag the user passed
explicitly untouched.

Resolution order (highest wins):

1. Explicit CLI flag.
2. ``--pipeline-preset`` value.
3. ``--image-preset`` value.
4. Hardcoded final defaults applied via :func:`fill_image_defaults` and
   :func:`fill_pipeline_defaults`.

For this layering to work, the argparse default of every preset-fillable,
non-boolean flag must be ``None`` — otherwise "user passed the default" and
"argparse filled the default" are indistinguishable and preset values would be
silently ignored. The real (documented) defaults live in
``_IMAGE_FINAL_DEFAULTS`` / ``_PIPELINE_FINAL_DEFAULTS`` below and are filled
after the preset layers.
"""

from __future__ import annotations

import argparse
import difflib
from pathlib import Path
from typing import Any

import yaml


# Flag names whose argparse dest differs from a simple hyphen→underscore swap.
_FLAG_TO_DEST: dict[str, str] = {
    "from": "start",
    "to": "end",
}


def _flag_to_dest(flag: str) -> str:
    """Map a hyphenated CLI flag name to its argparse ``dest``."""
    return _FLAG_TO_DEST.get(flag, flag.replace("-", "_"))


# ---- key allow-lists --------------------------------------------------------


_IMAGE_PRESET_KEYS: frozenset[str] = frozenset(
    {
        "provider",
        "size",
        "aspect-ratio",
        "quality",
        "output-format",
        "compression",
        "image-model",
    }
)


# Pipeline presets are scoped per pipeline because each pipeline accepts a
# different flag surface. Keep these allow-lists in sync with cli.py subparsers.
_PIPELINE_PRESET_KEYS: dict[str, frozenset[str]] = {
    "slide": frozenset(
        {
            "concurrent",
            "producers",
            "force",
            "batch-size",
            "mode",
            "visuals-only",
            "interleave",
            "skip-images",
            "from",
            "to",
        }
    ),
    "infographic": frozenset(
        {
            "variants",
            "critique",
            "critique-rounds",
            "skip-images",
            "from",
            "to",
        }
    ),
}


# ---- final defaults ---------------------------------------------------------


# Hardcoded defaults applied to image flags after preset resolution. Each
# pipeline historically had its own argparse default for --provider and
# --aspect-ratio; centralizing them here lets us switch the argparse defaults
# to None so we can detect "user didn't pass it" reliably.
_IMAGE_FINAL_DEFAULTS: dict[str, dict[str, Any]] = {
    "slide": {"provider": "gemini", "aspect_ratio": "16:9"},
    "infographic": {"provider": "gemini", "aspect_ratio": "16:9"},
}


# Hardcoded defaults for pipeline-preset-fillable flags, applied after preset
# resolution (same pattern as _IMAGE_FINAL_DEFAULTS). Keyed by argparse
# ``dest`` (so ``from``/``to`` appear as ``start``/``end``). The argparse
# defaults for these flags are None so preset values are not shadowed; the
# user-facing defaults documented in the ``help=`` strings live here.
# Keys whose argparse default is already None (concurrent, producers,
# target-scenes, target-frames, only-image, interleave, slide's batch-size)
# need no entry: None is their real default.
_PIPELINE_FINAL_DEFAULTS: dict[str, dict[str, Any]] = {
    "slide": {"start": "auto", "end": "images", "mode": "auto"},
    "infographic": {
        "start": "auto",
        "end": "images",
        "variants": 3,
        "critique_rounds": 1,
    },
}


# ---- YAML loading -----------------------------------------------------------


def _find_repo_root() -> Path:
    """Walk up from this module until a sibling ``pyproject.toml`` is found."""
    here = Path(__file__).resolve().parent
    while here != here.parent:
        if (here / "pyproject.toml").exists():
            return here
        here = here.parent
    # Fallback: assume <repo>/src/polyptych/ layout
    return Path(__file__).resolve().parent.parent.parent


def _load_yaml(filename: str) -> dict[str, Any]:
    path = _find_repo_root() / filename
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _suggest(name: str, candidates: list[str]) -> str:
    if not candidates:
        return ""
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=0.5)
    return f" (did you mean {matches[0]!r}?)" if matches else ""


def load_image_preset(name: str) -> dict[str, Any]:
    """Load a single image preset by name.

    Raises:
        ValueError: if the preset name is unknown or contains invalid keys.
    """
    presets = _load_yaml("image-presets.yaml")
    if name not in presets:
        suggestion = _suggest(name, sorted(presets.keys()))
        raise ValueError(
            f"Unknown image preset: {name!r}{suggestion}. "
            f"Available: {sorted(presets.keys())}"
        )
    raw: dict[str, Any] = presets[name] or {}
    bad = set(raw) - _IMAGE_PRESET_KEYS
    if bad:
        raise ValueError(
            f"Image preset {name!r} has unknown keys: {sorted(bad)}. "
            f"Valid keys: {sorted(_IMAGE_PRESET_KEYS)}"
        )
    return raw


def load_pipeline_preset(pipeline: str, name: str) -> dict[str, Any]:
    """Load a single pipeline preset by name from the given pipeline namespace.

    Raises:
        ValueError: if the pipeline namespace is missing, the name is unknown,
        or the preset contains invalid keys for this pipeline.
    """
    presets = _load_yaml("pipeline-presets.yaml")
    pipeline_presets: dict[str, Any] = presets.get(pipeline) or {}
    if not pipeline_presets:
        raise ValueError(
            f"No pipeline presets defined for {pipeline!r} "
            f"(looked for {name!r} in pipeline-presets.yaml)"
        )
    if name not in pipeline_presets:
        suggestion = _suggest(name, sorted(pipeline_presets.keys()))
        raise ValueError(
            f"Unknown pipeline preset {name!r} for {pipeline!r}{suggestion}. "
            f"Available: {sorted(pipeline_presets.keys())}"
        )
    raw: dict[str, Any] = pipeline_presets[name] or {}
    valid = _PIPELINE_PRESET_KEYS.get(pipeline, frozenset())
    bad = set(raw) - valid
    if bad:
        raise ValueError(
            f"Pipeline preset {pipeline!r}/{name!r} has unknown keys: "
            f"{sorted(bad)}. Valid keys for this pipeline: {sorted(valid)}"
        )
    return raw


# ---- application to argparse Namespace --------------------------------------


def _is_unset(value: Any) -> bool:
    """Treat ``None`` (preset-fillable default) as 'user did not pass it'."""
    return value is None


def _apply_layer(args: argparse.Namespace, layer: dict[str, Any]) -> None:
    """Fill any unset fields in ``args`` from a single preset layer.

    Values overwrite ``None``-valued attributes only. Boolean preset values are
    additive: if the preset says ``True`` and the current value is ``False``
    (the argparse store_true default), we set ``True`` — but a preset can never
    flip an explicit ``True`` back to ``False``.
    """
    for flag, value in layer.items():
        dest = _flag_to_dest(flag)
        current = getattr(args, dest, None)
        if isinstance(value, bool):
            if value and current is not True:
                setattr(args, dest, True)
            continue
        if _is_unset(current):
            setattr(args, dest, value)


def apply_presets(
    args: argparse.Namespace,
    *,
    pipeline: str,
    image_preset: str | None,
    pipeline_preset: str | None,
) -> None:
    """Fill ``args`` from named presets, then fill remaining final defaults.

    Mutates ``args`` in place. Call after ``parser.parse_args()`` and before
    any code reads image- or pipeline-related attributes (the argparse
    defaults for preset-fillable flags are ``None`` until this runs).

    Args:
        args: Parsed argparse namespace.
        pipeline: Internal pipeline name (slide, infographic).
        image_preset: Name of an entry in ``image-presets.yaml``, or None.
        pipeline_preset: Name of an entry in
            ``pipeline-presets.yaml[pipeline]``, or None.
    """
    if image_preset:
        _apply_layer(args, load_image_preset(image_preset))
    if pipeline_preset:
        _apply_layer(args, load_pipeline_preset(pipeline, pipeline_preset))
    fill_image_defaults(args, pipeline)
    fill_pipeline_defaults(args, pipeline)


def fill_image_defaults(args: argparse.Namespace, pipeline: str) -> None:
    """Apply hardcoded provider/aspect-ratio defaults for the given pipeline.

    Centralizes the per-pipeline defaults that were previously baked into each
    subparser's ``add_argument(... default=...)``. Argparse defaults for
    these flags are now ``None`` so explicit-vs-preset can be distinguished;
    this function fills any remaining ``None`` values.

    Aspect-ratio is size-aware: if ``--size`` is set (from CLI or preset) but
    ``--aspect-ratio`` is still unset, the aspect ratio is derived from the
    size rather than using the pipeline default. This prevents the pipeline
    default from contradicting an explicit size and lets run_config treat any
    remaining conflict as a genuine user error.
    """
    from .run_config import _derive_aspect_ratio_from_size

    defaults = _IMAGE_FINAL_DEFAULTS.get(pipeline, {})
    for dest, value in defaults.items():
        if getattr(args, dest, None) is not None:
            continue
        if dest == "aspect_ratio":
            derived = _derive_aspect_ratio_from_size(getattr(args, "size", None))
            if derived is not None:
                setattr(args, dest, derived)
                continue
        setattr(args, dest, value)


def fill_pipeline_defaults(args: argparse.Namespace, pipeline: str) -> None:
    """Apply hardcoded defaults for pipeline-preset-fillable flags.

    Centralizes the per-pipeline defaults (critique-rounds, subtype, variants,
    from/to, ...) that were previously baked into each subparser's
    ``add_argument(... default=...)``. With non-None argparse defaults,
    ``_apply_layer`` could not distinguish "user passed the default" from
    "argparse filled the default", so pipeline-preset values for those flags
    were silently ignored (e.g. ``infographic/critique``'s ``critique-rounds``).
    Argparse defaults are now ``None``; this function fills any value still
    unset after the preset layers.
    """
    defaults = dict(_PIPELINE_FINAL_DEFAULTS.get(pipeline, {}))
    for dest, value in defaults.items():
        if getattr(args, dest, None) is None:
            setattr(args, dest, value)
