"""Single source of truth for pipeline tasks.

Each task is described by a ``TaskSpec`` carrying its name, owning pipeline,
prompt filename, and (when applicable) the Pydantic output model, output
filename, position within the pipeline, and dependencies on other tasks.

The ``name`` keys match the strings used in ``model_config.yaml`` so the
two files can be cross-checked. The output/order/dependency fields mirror
the values currently kept in ``pipeline_config.py``; tests assert the two
representations stay aligned.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from .models import (
    Task1Output,
    Task2Output,
    Task3Output,
    Task4Output,
    Task5Output,
    Task6Output,
    Task7Output,
    TaskI0Output,
    TaskI1Output,
    TaskI2Output,
)

Pipeline = Literal[
    "slide",
    "infographic",
]


@dataclass(frozen=True)
class TaskSpec:
    """Metadata for a single pipeline task."""

    name: str
    pipeline: Pipeline
    prompt_filename: str
    supports_subtype: bool = False
    supports_genre: bool = False
    output_model: type[BaseModel] | None = None
    output_filename: str | None = None
    step_order: int | None = None
    dependencies: tuple[str, ...] = ()

    def resolve_prompt_filename(
        self,
        *,
        subtype: str | None = None,
        genre: str | None = None,
    ) -> str:
        """Return the prompt filename for this task with variant substitution.

        Slide task 6 (``supports_genre``) tries ``task-06-slide-specification-fiction.md``
        before falling back to ``task-06-slide-specification.md``.
        """
        if self.supports_subtype and subtype is not None:
            return f"{self.prompt_filename}-{subtype}.md"
        if self.supports_genre and genre is not None:
            return self.prompt_filename.replace(".md", f"-{genre}.md")
        return (
            self.prompt_filename
            if self.prompt_filename.endswith(".md")
            else f"{self.prompt_filename}.md"
        )


def _spec(
    name: str,
    pipeline: Pipeline,
    filename: str,
    *,
    model: type[BaseModel] | None = None,
    out: str | None = None,
    order: int | None = None,
    deps: tuple[str, ...] = (),
    supports_subtype: bool = False,
    supports_genre: bool = False,
) -> TaskSpec:
    return TaskSpec(
        name=name,
        pipeline=pipeline,
        prompt_filename=filename,
        supports_subtype=supports_subtype,
        supports_genre=supports_genre,
        output_model=model,
        output_filename=out,
        step_order=order,
        dependencies=deps,
    )


_TASK_LIST: list[TaskSpec] = [
    # Slide pipeline
    _spec(
        "task1",
        "slide",
        "task-01-genre-classification.md",
        model=Task1Output,
        out="task1-genre.yaml",
        order=1,
        deps=(),
    ),
    _spec(
        "task2",
        "slide",
        "task-02-source-analysis.md",
        model=Task2Output,
        out="task2-analysis.yaml",
        order=2,
        deps=("task1",),
    ),
    _spec(
        "task3",
        "slide",
        "task-03-structure-planning.md",
        model=Task3Output,
        out="task3-structure.yaml",
        order=3,
        deps=("task1", "task2"),
    ),
    _spec(
        "task4",
        "slide",
        "task-04-content-allocation.md",
        model=Task4Output,
        out="task4-content.yaml",
        order=4,
        deps=("task1", "task2", "task3"),
    ),
    _spec(
        "task5",
        "slide",
        "task-05-visual-design.md",
        model=Task5Output,
        out="task5-design.yaml",
        order=5,
        deps=("task1", "task2", "task4"),
    ),
    _spec(
        "task6",
        "slide",
        "task-06-slide-specification.md",
        supports_genre=True,
        model=Task6Output,
        out="task6-slides.yaml",
        order=6,
        deps=("task1", "task2", "task3", "task4", "task5"),
    ),
    _spec(
        "task7",
        "slide",
        "task-07-image-generation.md",
        model=Task7Output,
        out="task7-prompts.yaml",
        order=7,
        # task2 additionally supplies the fiction character canon, but stays a
        # soft dependency (pipeline_task._character_canon) so legacy output
        # dirs without task2-analysis.yaml can still resume from task7.
        deps=("task1", "task5", "task6"),
    ),
    # Infographic pipeline
    _spec(
        "i0",
        "infographic",
        "task-i0-analysis.md",
        model=TaskI0Output,
        out="task-i0-analysis.yaml",
        order=1,
        deps=(),
    ),
    _spec(
        "i1",
        "infographic",
        "task-i1-design.md",
        model=TaskI1Output,
        out="task-i1-design.yaml",
        order=2,
        deps=("i0",),
    ),
    _spec(
        "i2",
        "infographic",
        "task-i2-prompts.md",
        model=TaskI2Output,
        out="task-i2-prompts.yaml",
        order=3,
        deps=("i0", "i1"),
    ),
    _spec("i2_critique", "infographic", "task-i2-critique.md"),
    _spec("i2_refine", "infographic", "task-i2-refine.md"),
]


TASKS: dict[str, TaskSpec] = {spec.name: spec for spec in _TASK_LIST}


def get_task(name: str) -> TaskSpec:
    """Return the ``TaskSpec`` registered under ``name``.

    Raises ``KeyError`` with the list of known names when ``name`` is unknown.
    """
    try:
        return TASKS[name]
    except KeyError:
        known = ", ".join(sorted(TASKS))
        raise KeyError(f"Unknown task '{name}'. Known: {known}") from None


def tasks_for_pipeline(pipeline: Pipeline) -> list[TaskSpec]:
    """Return every ``TaskSpec`` whose pipeline matches ``pipeline``, in registry order."""
    return [spec for spec in _TASK_LIST if spec.pipeline == pipeline]


def register_tasks(specs: list[TaskSpec]) -> None:
    """Add extension-pipeline task specs to the registry.

    Appends to the ordered task list and the by-name lookup so a downstream
    package's tasks become first-class everywhere the registry is consulted —
    the step-map builders in ``pipeline_config``, prompt resolution via
    ``get_task``, and validation. Call once at import time. Raises ``ValueError``
    on a duplicate task name so two pipelines can't silently shadow each other.
    """
    for spec in specs:
        if spec.name in TASKS:
            raise ValueError(f"Task '{spec.name}' is already registered")
        _TASK_LIST.append(spec)
        TASKS[spec.name] = spec
