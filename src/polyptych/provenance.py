"""Shared, persistent text-task attribution for local and CLI runs."""

from __future__ import annotations

import contextlib
import os
import tempfile
from threading import RLock
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

PROVENANCE_FILENAME = "provenance.yaml"
_PROVENANCE_LOCK = RLock()


def _output_file_to_task() -> dict[str, str]:
    """Build the ``output filename -> task name`` reverse map.

    Sourced from the merged ``TASKS`` registry (core slide/infographic specs plus
    the extension specs, which register themselves on import), so it covers every
    tracked task of every pipeline. Imported locally to avoid an import-time cycle
    with ``pipeline`` and to pick up any late task registration.
    """
    from .task_registry import TASKS

    return {
        spec.output_filename: spec.name
        for spec in TASKS.values()
        if spec.output_filename
    }


def task_for_output_file(filename: str) -> str | None:
    """Return the task name that produces ``filename``, or None if untracked.

    ``filename`` may include subdirectories (e.g. ``prompts/item.yaml``); only the
    basename is matched against the registry, so ``manifest.yaml`` and other
    non-task outputs return None.
    """
    return _output_file_to_task().get(Path(filename).name)


def _atomic_write_yaml(path: Path, data: dict[str, Any]) -> None:
    """Write ``data`` to ``path`` atomically (tempfile + os.replace).

    Mirrors the core ``_save_yaml`` pattern so a crash mid-write can never leave a
    half-written provenance file behind.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        os.replace(tmp_path, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def read_metadata(path: Path) -> dict[str, Any]:
    """Read optional diagnostic YAML without making old outputs unloadable."""
    try:
        data = yaml.safe_load(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


def read_task_provenance(output_dir: Path) -> dict[str, dict[str, Any]]:
    """Merge legacy local attribution, manifest snapshots, and the sidecar.

    Only a local manifest with a single known author can seed task entries.
    Old CLI manifests listed configured defaults, so never infer authors from them.
    The sidecar takes precedence over the manifest snapshot.
    """
    manifest = read_metadata(output_dir / "manifest.yaml")
    tasks: dict[str, dict[str, Any]] = {}
    authors = manifest.get("models")
    if isinstance(authors, list) and len(authors) == 1:
        authors = authors[0]
    completed = manifest.get("tasks_completed", [])
    if (
        manifest.get("mode", manifest.get("text_mode")) == "local"
        and isinstance(authors, str)
        and isinstance(completed, list)
    ):
        for task in completed:
            if isinstance(task, str):
                tasks[task] = {
                    "mode": "local",
                    "model": authors,
                    "timestamp": manifest.get("timestamp"),
                }
    for data in (
        manifest.get("task_provenance"),
        read_metadata(output_dir / PROVENANCE_FILENAME).get("tasks"),
    ):
        if isinstance(data, dict):
            for task, entry in data.items():
                if isinstance(task, str) and isinstance(entry, dict):
                    tasks[task] = dict(entry)
    return tasks


def record_task_provenance(
    output_dir: Path,
    task: str,
    *,
    mode: str,
    model: str | None,
    timestamp: str | None = None,
    provider: str | None = None,
    model_source: str | None = None,
) -> None:
    """Merge one local author or successful API call into the sidecar.

    CLI callers pass model_source="response" with the returned model. Older
    CLI entries without a source describe configured models, not verified calls.
    Synchronize read/merge/write across worker threads to avoid lost entries.
    """
    with _PROVENANCE_LOCK:
        path = Path(output_dir) / PROVENANCE_FILENAME
        data = read_metadata(path)
        tasks = read_task_provenance(Path(output_dir))
        entry = {
            "mode": mode,
            "model": model,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "model_source": model_source,
        }
        tasks[task] = {k: v for k, v in entry.items() if v is not None}
        data["tasks"] = tasks
        try:
            _atomic_write_yaml(path, data)
        except OSError:
            # Provenance is diagnostic and must not break generation.
            pass
