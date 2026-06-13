"""Pipeline orchestration for slide generation.

Thin shim: ``SlidePipeline`` is built by inheriting from per-pipeline-type
mixins. ``__init__`` and shared plumbing live on ``SlidePipelineBase``.
Step constants and pure helpers live in ``pipeline_config`` and are
re-exported here so existing imports (``from polyptych.pipeline import …``)
keep working unchanged.
"""

from .pipeline_base import SlidePipelineBase
from .pipeline_config import (
    ALL_STEPS,
    INFOGRAPHIC_MODELS,
    INFOGRAPHIC_OUTPUT_FILES,
    INFOGRAPHIC_STEP_DEPENDENCIES,
    INFOGRAPHIC_STEPS,
    InfographicStepName,
    STEP_DEPENDENCIES,
    StepName,
    TASK_MODELS,
    TASK_OUTPUT_FILES,
    _make_step_logger,
    find_resume_step,
)
from .pipeline_infographic import SlidePipelineInfographicMixin
from .pipeline_task import SlidePipelineTaskMixin

# Public surface re-exported for ``from polyptych.pipeline import …`` callers.
# Declared explicitly so the lint pass treats these as intentional re-exports
# rather than unused imports (this is a facade module — see module docstring).
__all__ = [
    "SlidePipeline",
    "ALL_STEPS",
    "INFOGRAPHIC_MODELS",
    "INFOGRAPHIC_OUTPUT_FILES",
    "INFOGRAPHIC_STEP_DEPENDENCIES",
    "INFOGRAPHIC_STEPS",
    "InfographicStepName",
    "STEP_DEPENDENCIES",
    "StepName",
    "TASK_MODELS",
    "TASK_OUTPUT_FILES",
    "_make_step_logger",
    "find_resume_step",
]


class SlidePipeline(
    SlidePipelineTaskMixin,
    SlidePipelineInfographicMixin,
    SlidePipelineBase,
):
    """Orchestrates the slide and infographic pipelines.

    All methods live on the per-pipeline-type mixins. ``SlidePipelineBase``
    provides ``__init__`` and the cross-pipeline plumbing (model resolution,
    YAML I/O, manifest writing, ``ImageClient`` construction).
    """

    pass
