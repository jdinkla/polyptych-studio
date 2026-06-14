"""Stable extension API for building pipelines on top of the Polyptych core.

This module is the **single supported surface** for downstream packages that
add their own pipelines (extra steps, tasks, run-configs, and CLI subcommands)
without forking the core. It re-exports the registry builders, task-spec
primitives, run-config bases, preset tables, prompt loaders, the slide/
infographic pipeline mixins, and the CLI building blocks under stable public
names.

Why a dedicated module: the core keeps these helpers ``_``-private inside their
home modules so it stays free to refactor internals. ``ext`` pins the subset
that extensions are allowed to rely on. If an internal is renamed, this file is
the one place that breaks — a deliberate chokepoint, not an accident.

Recompose pattern (downstream): import the core's ``CORE_*`` tables/specs and
concatenate your own, reuse the builders to derive output/model/dependency maps,
subclass ``PipelineRunConfig``, compose ``SlidePipeline`` with your mixins, and
extend ``build_parser`` via the exported arg-adders and command handlers.
"""

from __future__ import annotations

# --- pipeline_config: step-map builders, slide/infographic tables, helpers ---
from .pipeline_config import (
    ALL_STEPS,
    INFOGRAPHIC_MODELS,
    INFOGRAPHIC_OUTPUT_FILES,
    INFOGRAPHIC_STEP_DEPENDENCIES,
    INFOGRAPHIC_STEPS,
    STEP_DEPENDENCIES,
    TASK_MODELS,
    TASK_OUTPUT_FILES,
    InfographicStepName,
    StepName,
    _build_models as build_models,
    _build_output_files as build_output_files,
    _build_step_deps as build_step_deps,
    _make_step_logger as make_step_logger,
    find_resume_step,
)

# --- task_registry: TaskSpec primitive, the core spec list, lookups ---
from .task_registry import (
    Pipeline as CorePipeline,
    TaskSpec,
    TASKS as CORE_TASKS,
    _TASK_LIST as CORE_TASK_SPECS,
    _spec as task_spec,
    get_task,
    register_tasks,
    tasks_for_pipeline,
)

# --- run_config: base run-config + shared option mixins/helpers ---
from .run_config import (
    InfographicRunConfig,
    PipelineRunConfig,
    SlideRunConfig,
    _ConcurrencyOptions as ConcurrencyOptions,
    _CritiqueOptions as CritiqueOptions,
    _common_image_kwargs as common_image_kwargs,
    _derive_aspect_ratio_from_size as derive_aspect_ratio_from_size,
)

# --- presets: the extendable lookup tables + the apply/fill pipeline ---
from .presets import (
    _IMAGE_FINAL_DEFAULTS as CORE_IMAGE_FINAL_DEFAULTS,
    _PIPELINE_FINAL_DEFAULTS as CORE_PIPELINE_FINAL_DEFAULTS,
    _PIPELINE_PRESET_KEYS as CORE_PIPELINE_PRESET_KEYS,
    _apply_layer as apply_layer,
    _flag_to_dest as flag_to_dest,
    apply_presets,
    fill_image_defaults,
    fill_pipeline_defaults,
    load_image_preset,
    load_pipeline_preset,
    register_pipeline_presets,
    register_preset_dir,
)

# --- prompt_loader: per-pipeline prompt resolution primitives ---
from .prompt_loader import (
    get_prompts_dir,
    _load_by_pipeline as load_by_pipeline,
    _pipeline_prompt_map as pipeline_prompt_map,
    _read_prompt_by_spec as read_prompt_by_spec,
    load_prompt_for,
    load_provider_guidelines,
    register_prompts_dir,
)

# --- pipeline: the composable slide/infographic base + mixins ---
from .pipeline_base import (
    IMAGE_GEN_AVAILABLE,
    PipelineMixin,
    SlidePipelineBase,
)
from .pipeline_infographic import SlidePipelineInfographicMixin
from .pipeline_task import SlidePipelineTaskMixin
from .pipeline import SlidePipeline

# --- image_batch: the building blocks for a pipeline's image step ---
from .image_batch import (
    BatchItem,
    BatchResult,
    BatchSettings,
    BuiltPrompt,
    ImageBatchGenerator,
    ImageFailure,
)

# --- cli: arg-adders, command handlers, parser + dispatch building blocks ---
from .cli import (
    _SUBCOMMAND_TO_PIPELINE as CORE_SUBCOMMAND_TO_PIPELINE,
    _add_advanced_image_args as add_advanced_image_args,
    _add_image_flags as add_image_flags,
    _add_image_model_arg as add_image_model_arg,
    _add_preset_flags as add_preset_flags,
    _add_text_provider_args as add_text_provider_args,
    _resolve_image_quality as resolve_image_quality,
    _resolve_ref_images as resolve_ref_images,
    _run_pipeline_command as run_pipeline_command,
    build_parser,
    clean_source_command,
    deck_command,
    infographic_command,
    parse_scene_selection,
    parse_slide_selection,
    register_image_quality_default,
    register_validation_pipeline,
    resolve_from_step,
    validate_command,
)

__all__ = [
    # pipeline_config
    "ALL_STEPS",
    "INFOGRAPHIC_MODELS",
    "INFOGRAPHIC_OUTPUT_FILES",
    "INFOGRAPHIC_STEP_DEPENDENCIES",
    "INFOGRAPHIC_STEPS",
    "STEP_DEPENDENCIES",
    "TASK_MODELS",
    "TASK_OUTPUT_FILES",
    "InfographicStepName",
    "StepName",
    "build_models",
    "build_output_files",
    "build_step_deps",
    "make_step_logger",
    "find_resume_step",
    # task_registry
    "CorePipeline",
    "TaskSpec",
    "CORE_TASKS",
    "CORE_TASK_SPECS",
    "task_spec",
    "get_task",
    "register_tasks",
    "tasks_for_pipeline",
    # run_config
    "InfographicRunConfig",
    "PipelineRunConfig",
    "SlideRunConfig",
    "ConcurrencyOptions",
    "CritiqueOptions",
    "common_image_kwargs",
    "derive_aspect_ratio_from_size",
    # presets
    "CORE_IMAGE_FINAL_DEFAULTS",
    "CORE_PIPELINE_FINAL_DEFAULTS",
    "CORE_PIPELINE_PRESET_KEYS",
    "apply_layer",
    "flag_to_dest",
    "apply_presets",
    "fill_image_defaults",
    "fill_pipeline_defaults",
    "load_image_preset",
    "load_pipeline_preset",
    "register_pipeline_presets",
    "register_preset_dir",
    # prompt_loader
    "get_prompts_dir",
    "load_by_pipeline",
    "pipeline_prompt_map",
    "read_prompt_by_spec",
    "load_prompt_for",
    "load_provider_guidelines",
    "register_prompts_dir",
    # pipeline
    "IMAGE_GEN_AVAILABLE",
    "PipelineMixin",
    "SlidePipelineBase",
    "SlidePipelineInfographicMixin",
    "SlidePipelineTaskMixin",
    "SlidePipeline",
    # image_batch
    "BatchItem",
    "BatchResult",
    "BatchSettings",
    "BuiltPrompt",
    "ImageBatchGenerator",
    "ImageFailure",
    # cli
    "CORE_SUBCOMMAND_TO_PIPELINE",
    "add_advanced_image_args",
    "add_image_flags",
    "add_image_model_arg",
    "add_preset_flags",
    "add_text_provider_args",
    "resolve_image_quality",
    "resolve_ref_images",
    "run_pipeline_command",
    "build_parser",
    "clean_source_command",
    "deck_command",
    "infographic_command",
    "parse_scene_selection",
    "parse_slide_selection",
    "register_image_quality_default",
    "register_validation_pipeline",
    "resolve_from_step",
    "validate_command",
]
