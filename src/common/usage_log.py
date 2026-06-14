"""JSONL logging for API usage (LLM, image generation)."""

import json
import threading
from pathlib import Path

from .compat import getenv_compat, runtime_write_dir

_log_lock = threading.Lock()


def default_usage_log() -> Path:
    """Return the default usage-log path, resolved at call time.

    Resolution order:
    1. ``$POLYPTYCH_USAGE_LOG`` env var (new name).
    2. ``$SLIDE_GEN_USAGE_LOG`` env var (deprecated alias; emits a one-time warning).
    3. ``~/.cache/polyptych/usage.jsonl`` (stable per-user default via
       :func:`common.compat.runtime_write_dir`).
    """
    env_val = getenv_compat("POLYPTYCH_USAGE_LOG", "SLIDE_GEN_USAGE_LOG")
    if env_val is not None:
        return Path(env_val)
    return runtime_write_dir("cache") / "usage.jsonl"


def log_usage(path: Path, entry: dict) -> None:
    """Append a single usage entry as one JSON line (thread-safe)."""
    line = json.dumps(entry, default=str) + "\n"
    with _log_lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
