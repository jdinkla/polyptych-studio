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


def _read_prompt_by_spec(
    spec: TaskSpec,
    *,
    subtype: str | None = None,
    genre: str | None = None,
) -> str:
    """Resolve ``spec`` to a file under ``prompts/tasks/`` and return its text.

    For genre-supporting tasks the genre-specific variant is tried first and
    the base filename is used as a fallback.
    """
    prompts_dir = get_prompts_dir()

    if spec.supports_genre and genre is not None:
        variant = prompts_dir / spec.resolve_prompt_filename(genre=genre)
        if variant.exists():
            return variant.read_text()

    filename = spec.resolve_prompt_filename(subtype=subtype)
    prompt_file = prompts_dir / filename
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    return prompt_file.read_text()


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
