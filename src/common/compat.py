"""Backward-compatible resolution of renamed env vars and runtime directories.

The Polyptych rebrand renamed user-facing env vars from the ``SLIDE_GEN_*``
namespace to ``POLYPTYCH_*`` and runtime directories from ``slide-analysis`` to
``polyptych``. To avoid breaking existing setups, the old names are honored as
deprecated fallbacks: the new name/location takes precedence, the old one is
used only when the new is absent, and a one-time warning is logged on first use.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import overload

logger = logging.getLogger("polyptych")

APP_NAME = "polyptych"
LEGACY_APP_NAME = "slide-analysis"

# Module-global so the deprecation warning fires at most once per process per name.
_warned_env: set[str] = set()


@overload
def getenv_compat(new_name: str, old_name: str, default: str) -> str: ...
@overload
def getenv_compat(new_name: str, old_name: str, default: None = None) -> str | None: ...


def getenv_compat(
    new_name: str, old_name: str, default: str | None = None
) -> str | None:
    """Read ``new_name`` from the environment, falling back to ``old_name``.

    Precedence: ``$new_name`` > ``$old_name`` (deprecated) > ``default``. The
    first time the deprecated ``old_name`` supplies the value, a one-time
    warning is emitted on the ``polyptych`` logger. Matches ``os.environ.get``
    semantics: an env var set to the empty string counts as set.
    """
    value = os.environ.get(new_name)
    if value is not None:
        return value
    legacy = os.environ.get(old_name)
    if legacy is not None:
        if old_name not in _warned_env:
            _warned_env.add(old_name)
            logger.warning(
                "Environment variable %s is deprecated and will be removed in a "
                "future release; use %s instead.",
                old_name,
                new_name,
            )
        return legacy
    return default


def _runtime_base(kind: str) -> Path:
    """Base dir for a runtime ``kind`` — ``config`` → ~/.config, ``cache`` → ~/.cache."""
    return Path.home() / f".{kind}"


def runtime_dirs(kind: str) -> tuple[Path, Path]:
    """Return ``(new, legacy)`` runtime dirs for ``kind`` (``config`` or ``cache``)."""
    base = _runtime_base(kind)
    return base / APP_NAME, base / LEGACY_APP_NAME


def resolve_runtime_file(kind: str, filename: str) -> Path | None:
    """First existing ``filename`` across the new then legacy runtime dir, or ``None``."""
    new, legacy = runtime_dirs(kind)
    for directory in (new, legacy):
        candidate = directory / filename
        if candidate.exists():
            return candidate
    return None


def runtime_write_dir(kind: str) -> Path:
    """Dir that new runtime files should be written to.

    Prefers the new ``polyptych`` namespace, but keeps writing into an existing
    legacy ``slide-analysis`` dir when that is the only one present, so a user's
    credentials/state stay consolidated in one location rather than split across
    two.
    """
    new, legacy = runtime_dirs(kind)
    if not new.exists() and legacy.exists():
        return legacy
    return new
