"""Central logging configuration for polyptych.

CLI entry points should call :func:`configure_logging` once at startup.
Library modules should use ``logger = logging.getLogger(__name__)`` and
emit at the usual ``debug/info/warning/error`` levels; this module wires
those up to stderr (and optionally a file) using a consistent format.

The actual configuration logic lives in :mod:`common.logging_setup`.
This module is the polyptych-flavored wrapper: it binds the ``polyptych``
logger name and keeps the historical signature that tests rely on.

Status prints that predate this module (``_make_step_logger`` in
``pipeline.py`` and ``ref_utils.py``, end-user messages in ``cli.py``)
intentionally remain on ``print``: they are interactive feedback, not
log events.
"""

from __future__ import annotations

import logging
from pathlib import Path

from common.logging_setup import (
    DATE_FORMAT,
    ENV_VAR,
    LEGACY_ENV_VAR,
    LOG_FORMAT,
)
from common.logging_setup import configure_logging as _configure_logging
from common.logging_setup import reset_logging as _reset_logging

__all__ = [
    "DATE_FORMAT",
    "ENV_VAR",
    "LEGACY_ENV_VAR",
    "LOG_FORMAT",
    "LOGGER_NAME",
    "configure_logging",
    "reset_logging",
]

LOGGER_NAME = "polyptych"


def configure_logging(
    level: str | int | None = None,
    log_file: str | Path | None = None,
    *,
    force: bool = False,
) -> logging.Logger:
    """Install stderr (and optional file) handlers on the ``polyptych`` logger.

    Level resolution order: explicit ``level`` argument, then the
    ``POLYPTYCH_LOG_LEVEL`` env var (deprecated alias ``SLIDE_GEN_LOG_LEVEL``),
    then ``INFO``. Safe to call more than
    once — repeat calls are ignored unless ``force=True``, which swaps the
    handlers so a CLI flag can override the env var.
    """
    return _configure_logging(LOGGER_NAME, level, log_file, force=force)


def reset_logging() -> None:
    """Drop all handlers and mark the logger unconfigured. Used by tests."""
    _reset_logging(LOGGER_NAME)
