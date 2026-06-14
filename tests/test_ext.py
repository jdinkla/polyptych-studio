"""The ``polyptych.ext`` extension API is a public contract.

These tests pin that contract: every name in ``__all__`` must be importable,
and a few load-bearing seams (the registry builders, the core spec list, the
run-config base, the pipeline mixins, the CLI parser builder) must keep working
so downstream extension packages don't break on a core refactor.
"""

import polyptych.ext as ext


def test_all_names_are_importable():
    missing = [name for name in ext.__all__ if not hasattr(ext, name)]
    assert not missing, f"names in __all__ not bound in module: {missing}"


def test_core_task_specs_match_registry():
    from polyptych.task_registry import _TASK_LIST

    assert ext.CORE_TASK_SPECS is _TASK_LIST
    assert len(ext.CORE_TASK_SPECS) > 0


def test_builders_produce_maps_for_core_steps():
    out = ext.build_output_files(ext.ALL_STEPS, {})
    models = ext.build_models(ext.ALL_STEPS, {})
    deps = ext.build_step_deps(ext.ALL_STEPS, {})
    assert out and models and deps


def test_run_config_base_is_subclassable():
    from dataclasses import dataclass

    @dataclass(frozen=True, kw_only=True)
    class _Demo(ext.PipelineRunConfig):
        pass

    assert issubclass(_Demo, ext.PipelineRunConfig)


def test_slide_pipeline_and_mixins_exposed():
    assert issubclass(ext.SlidePipeline, ext.SlidePipelineBase)


def test_build_parser_is_callable():
    parser = ext.build_parser()
    assert parser is not None
