"""Load prompt templates from prompts/tasks/ directory.

All task metadata lives in :mod:`polyptych.task_registry`; the functions
below are thin wrappers that stay for back-compat with existing call sites
in ``tasks/`` modules.
"""

from pathlib import Path

from .task_registry import (
    TASKS,
    Pipeline,
    TaskSpec,
    get_task,
    tasks_for_pipeline,
)


def get_prompts_dir() -> Path:
    """Return the path to ``prompts/tasks/`` at the repo root."""
    current_file = Path(__file__)
    # src/polyptych/prompt_loader.py -> project root is two parents up
    project_root = current_file.parent.parent.parent
    prompts_dir = project_root / "prompts" / "tasks"

    if not prompts_dir.exists():
        raise FileNotFoundError(f"Prompts directory not found: {prompts_dir}")

    return prompts_dir


# Additional ``prompts/tasks/`` directories registered by extension packages.
# Searched after the core directory so a downstream package's task prompts
# (which live in its own repo) resolve through the same loaders as the
# built-in ones. See :func:`register_prompts_dir`.
_EXTRA_PROMPT_DIRS: list[Path] = []


def register_prompts_dir(path: Path | str) -> None:
    """Register an extra ``prompts/tasks/`` directory for prompt resolution.

    Lets an extension package add the directory holding its own task prompts so
    ``load_prompt_for`` / ``_read_prompt_by_spec`` find them alongside the core
    prompts. Call once at import time. Idempotent; missing dirs raise.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Prompts directory not found: {p}")
    if p not in _EXTRA_PROMPT_DIRS:
        _EXTRA_PROMPT_DIRS.append(p)


def _prompt_search_dirs() -> list[Path]:
    """Core prompts dir first, then any extension-registered dirs."""
    return [get_prompts_dir(), *_EXTRA_PROMPT_DIRS]


def _read_prompt_by_spec(
    spec: TaskSpec,
    *,
    subtype: str | None = None,
    genre: str | None = None,
) -> str:
    """Resolve ``spec`` to a file under a ``prompts/tasks/`` dir and return its text.

    Searches the core prompts directory first, then any directories registered
    by extension packages (:func:`register_prompts_dir`). For genre-supporting
    tasks the genre-specific variant is tried first and the base filename is
    used as a fallback.
    """
    search_dirs = _prompt_search_dirs()

    if spec.supports_genre and genre is not None:
        genre_name = spec.resolve_prompt_filename(genre=genre)
        for d in search_dirs:
            variant = d / genre_name
            if variant.exists():
                return variant.read_text()

    filename = spec.resolve_prompt_filename(subtype=subtype)
    for d in search_dirs:
        prompt_file = d / filename
        if prompt_file.exists():
            return prompt_file.read_text()

    tried = ", ".join(str(d / filename) for d in search_dirs)
    raise FileNotFoundError(f"Prompt file not found: {filename} (searched: {tried})")


def load_prompt_for(
    task_name: str,
    *,
    subtype: str | None = None,
    genre: str | None = None,
) -> str:
    """Load a prompt by registry task name.

    Prefer this over the pipeline-specific loaders below; those exist only
    so existing callers keep working.
    """
    return _read_prompt_by_spec(get_task(task_name), subtype=subtype, genre=genre)


# ---- slide pipeline --------------------------------------------------------

# Legacy: slide tasks keyed by integer. Derived from the registry so the two
# cannot drift.
TASK_PROMPTS: dict[int, str] = {
    int(spec.name.removeprefix("task")): spec.prompt_filename
    for spec in tasks_for_pipeline("slide")
}


def load_task_prompt(task_number: int, genre: str | None = None) -> str:
    """Load a slide-pipeline task prompt (tasks 1-7), optionally genre-specific."""
    if task_number not in TASK_PROMPTS:
        raise ValueError(f"Invalid task number: {task_number}. Must be 1-7.")
    return _read_prompt_by_spec(get_task(f"task{task_number}"), genre=genre)


def load_all_prompts() -> dict[int, str]:
    """Load every slide-pipeline task prompt keyed by task number."""
    return {n: load_task_prompt(n) for n in TASK_PROMPTS}


# ---- per-pipeline loaders (back-compat) -----------------------------------


def _pipeline_prompt_map(pipeline: Pipeline) -> dict[str, str]:
    return {spec.name: spec.prompt_filename for spec in tasks_for_pipeline(pipeline)}


INFOGRAPHIC_TASK_PROMPTS: dict[str, str] = _pipeline_prompt_map("infographic")


def _load_by_pipeline(pipeline: Pipeline, task_name: str) -> str:
    spec = TASKS.get(task_name)
    if spec is None or spec.pipeline != pipeline:
        known = ", ".join(repr(s.name) for s in tasks_for_pipeline(pipeline))
        raise ValueError(
            f"Invalid {pipeline} task name: {task_name}. Must be one of: {known}."
        )
    return _read_prompt_by_spec(spec)


def load_infographic_task_prompt(task_name: str) -> str:
    """Load an infographic-pipeline task prompt by task name."""
    return _load_by_pipeline("infographic", task_name)


# ---- provider guidelines ---------------------------------------------------


def get_providers_dir() -> Path:
    """Return the path to ``prompts/providers/`` at the repo root."""
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return project_root / "prompts" / "providers"


def load_provider_guidelines(provider: str) -> str | None:
    """Load provider-specific image prompt best practices, or ``None`` if absent."""
    guidelines_path = get_providers_dir() / f"{provider}-best-practices.md"
    if guidelines_path.exists():
        return guidelines_path.read_text()
    return None


__all__ = [
    "TASK_PROMPTS",
    "INFOGRAPHIC_TASK_PROMPTS",
    "get_prompts_dir",
    "get_providers_dir",
    "load_task_prompt",
    "load_all_prompts",
    "load_infographic_task_prompt",
    "load_provider_guidelines",
    "load_prompt_for",
]
