"""Locate the package's runtime data files (config YAMLs and prompt trees).

Several files that the pipelines read at runtime live at the repo root in
source form — ``model_config.yaml``, ``image_model_config.yaml``, the
``*-presets.yaml`` tables, and the whole ``prompts/`` tree. None of those sit
inside the ``polyptych`` import package, so a plain ``pip install`` wheel that
ships only ``.py`` modules can't find them.

The build bundles a copy under ``polyptych/_data/`` (see the
``[tool.hatch.build.targets.wheel.force-include]`` block in ``pyproject.toml``).
At runtime :func:`data_root` returns that bundled directory when it exists
(installed wheel) and otherwise falls back to the repo root (editable / source
checkout, where the files live unbundled). Every loader resolves its paths
through here so both layouts work identically.

We resolve via ``__file__`` rather than ``importlib.resources`` because the
prompt loaders glob directory trees and read many files; a real filesystem
``Path`` is far simpler than juggling ``Traversable`` handles, and a normal
(non-zip) wheel install exposes these as ordinary files anyway.
"""

from __future__ import annotations

from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
_BUNDLED_DATA = _PKG_DIR / "_data"


def data_root() -> Path:
    """Return the directory holding packaged runtime data.

    Installed wheel: ``polyptych/_data`` (populated at build time). Editable or
    source checkout: the repo root two levels up from this package, where the
    config YAMLs and ``prompts/`` tree live unbundled.
    """
    if _BUNDLED_DATA.is_dir():
        return _BUNDLED_DATA
    return _PKG_DIR.parent.parent  # src/polyptych -> src -> repo root


def data_path(*parts: str) -> Path:
    """Resolve a file or directory under :func:`data_root`."""
    return data_root().joinpath(*parts)
