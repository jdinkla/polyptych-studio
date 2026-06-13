"""Shared logging configuration helper for the CLI entry point.

The ``polyptych`` CLI installs handlers on a named logger at startup so
library modules can use ``logger = logging.getLogger(__name__)`` and emit
diagnostics at the usual ``debug/info/warning/error`` levels without each
module wiring up its own output. ``polyptych.logging_setup`` is a thin
wrapper over this for the ``polyptych`` logger (kept separate because its
public API is pinned by tests).

This lives in ``common`` — the lowest shared layer — so the configurator can
be reused without coupling modules together.

User-facing CLI output (transcripts, timing tables, file paths, summaries)
stays on ``print`` to stdout; only diagnostics flow through these loggers.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from common.compat import getenv_compat

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
ENV_VAR = "POLYPTYCH_LOG_LEVEL"
LEGACY_ENV_VAR = "SLIDE_GEN_LOG_LEVEL"

_configured: set[str] = set()


def resolve_level(level: str | int | None) -> int:
    """Turn a user-supplied level (name, int, or ``None``) into a ``logging`` int."""
    if level is None:
        env = getenv_compat(ENV_VAR, LEGACY_ENV_VAR)
        level = env if env else "INFO"
    if isinstance(level, int):
        return level
    try:
        return getattr(logging, level.upper())
    except AttributeError as err:
        raise ValueError(
            f"Unknown log level: {level!r}. "
            "Use DEBUG, INFO, WARNING, ERROR, or CRITICAL."
        ) from err


def configure_logging(
    logger_name: str,
    level: str | int | None = None,
    log_file: str | Path | None = None,
    *,
    force: bool = False,
) -> logging.Logger:
    """Install stderr (and optional file) handlers on the named logger.

    Level resolution order: explicit ``level`` argument, then the
    ``POLYPTYCH_LOG_LEVEL`` env var (deprecated alias ``SLIDE_GEN_LOG_LEVEL``),
    then ``INFO``. Safe to call more than once for a given ``logger_name`` —
    repeat calls are ignored unless ``force=True``, which swaps the handlers so
    a CLI flag can override the env var.
    """
    logger = logging.getLogger(logger_name)
    if logger_name in _configured and not force:
        return logger

    if force:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

    logger.setLevel(resolve_level(level))
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    if log_file is not None:
        file_handler = logging.FileHandler(Path(log_file), encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False  # stop log records from double-printing via root
    _configured.add(logger_name)
    return logger


def reset_logging(logger_name: str) -> None:
    """Drop all handlers and mark the named logger unconfigured. Used by tests."""
    logger = logging.getLogger(logger_name)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    _configured.discard(logger_name)
