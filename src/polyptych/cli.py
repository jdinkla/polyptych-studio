"""Command-line interface for slide generation pipeline."""

import argparse
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from common.compat import getenv_compat
from . import presets
from .logging_setup import configure_logging
from .model_config import load_image_model_config, load_model_config
from .pipeline import (
    SlidePipeline,
    ALL_STEPS,
    INFOGRAPHIC_STEPS,
    TASK_OUTPUT_FILES,
    TASK_MODELS,
    INFOGRAPHIC_OUTPUT_FILES,
    INFOGRAPHIC_MODELS,
    find_resume_step,
)
from .providers import list_all_text_providers
from .providers.base import TransientProviderError
from .run_config import (
    InfographicRunConfig,
    PipelineRunConfig,
    SlideRunConfig,
)

logger = logging.getLogger(__name__)


def _add_text_provider_args(parser: argparse.ArgumentParser) -> None:
    """Add --text-provider and --text-fallback arguments to a subparser."""
    parser.add_argument(
        "--text-provider",
        type=str,
        choices=list_all_text_providers(),
        default="gemini",
        help="Text generation provider (default: gemini)",
    )
    parser.add_argument(
        "--text-fallback",
        nargs="*",
        default=None,
        help="Text fallback provider chain. Omit for auto (all other providers). "
        "Use 'none' to disable fallback.",
    )


def _add_image_model_arg(parser: argparse.ArgumentParser) -> None:
    """Add --image-model argument to a subparser."""
    parser.add_argument(
        "--image-model",
        type=str,
        default=None,
        help="Override image generation model for this run (all providers). "
        "Also settable via POLYPTYCH_IMAGE_MODEL env var (deprecated alias: SLIDE_GEN_IMAGE_MODEL).",
    )


def _add_advanced_image_args(parser: argparse.ArgumentParser) -> None:
    """Add --ref-image, --output-format, --compression to a subparser.

    These flags only have effect on providers that support them. Today that's
    primarily OpenAI gpt-image-2 for output_format/compression, and
    openai/gemini for reference images.
    """
    parser.add_argument(
        "--ref-image",
        action="append",
        default=None,
        metavar="PATH",
        help="Path to a reference image (brand asset, source chart, exemplar). "
        "Repeat for multiple. Applied to every slide. Requires a provider "
        "that supports reference images (openai gpt-image-2, gemini).",
    )
    parser.add_argument(
        "--output-format",
        choices=["png", "jpeg", "webp"],
        default=None,
        help="Output image format. OpenAI gpt-image-2 only; other providers "
        "always emit PNG. Default: png.",
    )
    parser.add_argument(
        "--compression",
        type=int,
        default=None,
        metavar="N",
        help="Compression level 0-100 for --output-format jpeg or webp. "
        "OpenAI gpt-image-2 only.",
    )


def _add_image_flags(parser: argparse.ArgumentParser) -> None:
    """Add the four common image flags + advanced image flags to a subparser.

    Defaults are ``None`` so that preset application can detect "user did not
    pass it" reliably. Per-pipeline final defaults (e.g. ``provider=gemini``,
    ``aspect_ratio=16:9``) are filled in by
    :func:`presets.fill_image_defaults` after preset resolution.
    """
    parser.add_argument(
        "--provider",
        "-p",
        type=str,
        choices=["gemini", "openai", "xai", "vertex"],
        default=None,
        help="Image generation provider (default: gemini).",
    )
    parser.add_argument(
        "--size",
        "-s",
        type=str,
        default=None,
        help="Output image size. gpt-image-2: any WxH with both dimensions "
        "divisible by 16, aspect ratio within [1:3, 3:1], max edge 3840 — "
        "e.g. 1024x1024, 1024x1536, 1536x1024, 1152x2048 (true 9:16), "
        "2048x1152 (true 16:9), 2560x1440, 3840x2160. Gemini: 1K, 2K.",
    )
    parser.add_argument(
        "--quality",
        "-q",
        type=str,
        choices=["low", "medium", "high", "auto"],
        default=None,
        help="Quality (OpenAI gpt-image-2 only). Defaults to high for "
        "slide and infographic.",
    )
    parser.add_argument(
        "--aspect-ratio",
        "-a",
        type=str,
        choices=["16:9", "4:3", "3:4", "9:16", "1:1"],
        default=None,
        help="Aspect ratio (default: 16:9).",
    )
    _add_advanced_image_args(parser)


def _add_preset_flags(parser: argparse.ArgumentParser) -> None:
    """Add ``--image-preset`` and ``--pipeline-preset`` to a subparser.

    Presets are resolved before any code reads image-related attributes;
    explicit flags always win. See ``image-presets.yaml`` and
    ``pipeline-presets.yaml`` at the repo root.
    """
    parser.add_argument(
        "--image-preset",
        type=str,
        default=None,
        metavar="NAME",
        help="Apply a named image preset from image-presets.yaml "
        "(provider/size/aspect-ratio/quality bundle, reusable across pipelines).",
    )
    parser.add_argument(
        "--pipeline-preset",
        type=str,
        default=None,
        metavar="NAME",
        help="Apply a named pipeline preset from pipeline-presets.yaml "
        "(concurrency + pipeline-specific behavior bundle, scoped per pipeline).",
    )


# Map CLI subcommand → internal pipeline name used in presets and run_config.
_SUBCOMMAND_TO_PIPELINE: dict[str, str] = {
    "deck": "slide",
    "infographic": "infographic",
}


_OPENAI_DEFAULT_QUALITY = {
    "slide": "high",
    "infographic": "high",
}


def _resolve_image_quality(args: argparse.Namespace, pipeline_name: str) -> str | None:
    """Resolve --quality with per-pipeline OpenAI defaults.

    Slide and infographic both default to 'high' on OpenAI gpt-image-2.
    Other providers and explicit --quality values pass through unchanged.
    """
    explicit = args.quality if hasattr(args, "quality") and args.quality else None
    if explicit is not None:
        return explicit
    if getattr(args, "provider", None) == "openai":
        return _OPENAI_DEFAULT_QUALITY.get(pipeline_name)
    return None


def _resolve_ref_images(args: argparse.Namespace) -> list[str]:
    """Combine --ref-image flags with the style-preset's companion exemplar.

    Order: style exemplar first (anchors visual style), then user-supplied
    --ref-image paths in the order given. Returns empty list when no refs apply.
    """
    from .ref_utils import find_style_exemplar

    refs: list[str] = []
    style_path = getattr(args, "style", None)
    exemplar = find_style_exemplar(style_path) if style_path else None
    if exemplar is not None:
        refs.append(str(exemplar))
    user_refs = getattr(args, "ref_image", None) or []
    refs.extend(user_refs)
    return refs


def parse_slide_selection(selection: str) -> list[int]:
    """Parse slide selection string into list of slide numbers.

    Args:
        selection: Comma-separated list of slide numbers or ranges.
            Examples: "1,3", "1-3", "1-3,5,8-10"

    Returns:
        Sorted list of unique slide numbers.
    """
    slides = set()
    for part in selection.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            slides.update(range(int(start), int(end) + 1))
        else:
            slides.add(int(part))
    return sorted(slides)


def parse_scene_selection(selection: str) -> list[int]:
    """Parse scene selection string into list of scene numbers.

    Args:
        selection: Comma-separated list of scene numbers or ranges.
            Examples: "1,3", "1-3", "1-3,5,8-10"

    Returns:
        Sorted list of unique scene numbers.
    """
    scenes = set()
    for part in selection.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            scenes.update(range(int(start), int(end) + 1))
        else:
            scenes.add(int(part))
    return sorted(scenes)


def resolve_from_step(
    args_start: str,
    output_dir: Path,
    steps: list[str],
    output_files: dict[str, str],
    models: dict[str, type],
    force: bool = False,
) -> str:
    """Resolve the --from step, supporting 'auto' for auto-resume.

    If args_start is 'auto', walks the output directory to find the first
    step that needs to be (re)run. Explicit step names pass through unchanged.
    """
    if args_start != "auto":
        return args_start
    if force:
        return steps[0]
    resume = find_resume_step(output_dir, steps, output_files, models)
    if resume is None:
        # All tracked steps done — jump to first untracked step (prompts/images)
        first_untracked = next((s for s in steps if s not in output_files), steps[-1])
        return first_untracked
    if resume == steps[0]:
        print("No existing outputs found. Starting from scratch.")
    else:
        prev_idx = steps.index(resume) - 1
        prev = steps[prev_idx]
        print(f"Auto-resume: outputs valid through '{prev}'. Resuming from '{resume}'.")
    return resume


def _run_pipeline_command(
    args: argparse.Namespace,
    *,
    default_output_dir: str,
    steps: list[str],
    output_files: dict[str, str],
    models: dict[str, type],
    make_run_config: Callable[..., PipelineRunConfig],
    run_method: str,
    selection: tuple[str, str, Callable[[str], list[int]]] | None = None,
    pass_force: bool = False,
    pipeline_kwargs: Callable[[argparse.Namespace], dict[str, Any]] | None = None,
    validate_args: Callable[[argparse.Namespace], str | None] | None = None,
    start_override: Callable[[argparse.Namespace], str | None] | None = None,
    pipeline_cls: type | None = None,
) -> int:
    """Shared driver behind every pipeline subcommand.

    Each handler (``deck_command``, ``infographic_command``) is a thin
    declaration over this helper, which performs the common sequence: source
    validation, model/env resolution, ``--text-fallback`` normalization,
    image-config loading, pipeline construction, ``--from`` resolution, run
    dispatch, and the shared exception handling.

    Args:
        args: Parsed command-line arguments.
        default_output_dir: Directory used when ``--output-dir`` is omitted.
        steps: Ordered pipeline step names (for ``--from auto`` resolution).
        output_files: Step name → output filename registry.
        models: Step name → Pydantic model registry.
        make_run_config: The ``from_namespace`` classmethod of the pipeline's
            run-config dataclass.
        run_method: Name of the ``pipeline_cls`` method that runs the pipeline.
        selection: Optional ``(args attribute, from_namespace kwarg, parser)``
            triple for item-selection flags (``--slides``).
        pass_force: Whether this pipeline forwards ``--force`` to
            :func:`resolve_from_step` (slide only).
        pipeline_kwargs: Optional extra ``SlidePipeline`` constructor kwargs
            derived from args.
        validate_args: Optional pre-flight check run after the source-file
            check; returns an error message to print (exit 1), or None.
        start_override: Optional ``--from`` override; returns a step name, or
            None to fall through to the default resolution.
        pipeline_cls: Pipeline class to construct. Defaults to ``SlidePipeline``;
            extension packages pass their own composed class so ``run_method``
            can resolve to a mixin the core does not ship.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    # Resolve at call time (not as a default arg value) so the name lookup honors
    # any monkeypatch of ``polyptych.cli.SlidePipeline`` and so extensions can
    # inject their own composed class.
    if pipeline_cls is None:
        pipeline_cls = SlidePipeline

    source_path = Path(args.source_file)
    if not source_path.exists():
        print(f"Error: Source file not found: {source_path}", file=sys.stderr)
        return 1

    if validate_args is not None:
        error = validate_args(args)
        if error is not None:
            print(error, file=sys.stderr)
            return 1

    output_dir = Path(args.output_dir) if args.output_dir else Path(default_output_dir)

    try:
        override = args.model or getenv_compat("POLYPTYCH_MODEL", "SLIDE_GEN_MODEL")
        model_config = load_model_config(override=override)

        text_fallback = args.text_fallback
        if text_fallback is not None and len(text_fallback) == 0:
            text_fallback = None  # nargs="*" with no values = empty list, treat as auto

        image_model_override = args.image_model or getenv_compat(
            "POLYPTYCH_IMAGE_MODEL", "SLIDE_GEN_IMAGE_MODEL"
        )
        image_model_config = load_image_model_config(override=image_model_override)

        pipeline = pipeline_cls(
            source_path=source_path,
            output_dir=output_dir,
            model_config=model_config,
            image_model_config=image_model_config,
            text_provider=args.text_provider,
            text_fallback=text_fallback,
            **(pipeline_kwargs(args) if pipeline_kwargs is not None else {}),
        )

        config_kwargs: dict[str, Any] = {}
        if selection is not None:
            attr, kwarg, parse_selection = selection
            raw = getattr(args, attr)
            config_kwargs[kwarg] = parse_selection(raw) if raw else None

        from_step = start_override(args) if start_override is not None else None
        if from_step is None:
            from_step = resolve_from_step(
                args.start,
                output_dir,
                steps,
                output_files,
                models,
                force=(args.force if hasattr(args, "force") else False)
                if pass_force
                else False,
            )

        getattr(pipeline, run_method)(
            make_run_config(args, from_step=from_step, **config_kwargs)
        )

        if pipeline.image_failures:
            print(
                f"\nError: {len(pipeline.image_failures)} image(s) failed to generate:",
                file=sys.stderr,
            )
            for failure in pipeline.image_failures:
                print(f"  - {failure}", file=sys.stderr)
            print(
                "Re-run the same command to retry only the missing images.",
                file=sys.stderr,
            )
            return 1

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except TransientProviderError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception("Unexpected error in pipeline command")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def infographic_command(args: argparse.Namespace) -> int:
    """Handle the infographic command."""
    return _run_pipeline_command(
        args,
        default_output_dir="infographic_output",
        steps=INFOGRAPHIC_STEPS,
        output_files=INFOGRAPHIC_OUTPUT_FILES,
        models=INFOGRAPHIC_MODELS,
        make_run_config=InfographicRunConfig.from_namespace,
        run_method="run_infographic_pipeline",
    )


def validate_command(args: argparse.Namespace) -> int:
    """Validate task YAML outputs against their Pydantic schemas.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 if all valid, 1 if any invalid).
    """
    import json

    output_dir = Path(args.output_dir)
    if not output_dir.is_dir():
        print(f"Error: Directory not found: {output_dir}", file=sys.stderr)
        return 1

    # All pipeline registries: (pipeline_name, steps, output_files, models)
    PIPELINES = [
        ("slide", ALL_STEPS, TASK_OUTPUT_FILES, TASK_MODELS),
        (
            "infographic",
            INFOGRAPHIC_STEPS,
            INFOGRAPHIC_OUTPUT_FILES,
            INFOGRAPHIC_MODELS,
        ),
    ]

    # Build unified lookup: task_name → (pipeline, filename, model_class)
    task_registry: dict[str, tuple[str, str, type]] = {}
    for pipeline_name, _steps, output_files, models in PIPELINES:
        for task_name, filename in output_files.items():
            key = (
                task_name
                if task_name not in task_registry
                else f"{pipeline_name}:{task_name}"
            )
            task_registry[key] = (pipeline_name, filename, models[task_name])

    def _validate_one(task_name: str, filename: str, model_class: type) -> dict:
        """Validate a single task output file. Returns a result dict."""
        filepath = output_dir / filename
        result = {
            "task": task_name,
            "file": filename,
            "status": "missing",
            "error": None,
        }
        if not filepath.exists():
            return result
        try:
            import yaml as _yaml

            content = filepath.read_text()
            if not content.strip():
                result["status"] = "empty"
                return result
            data = _yaml.safe_load(content)
            if data is None:
                result["status"] = "empty"
                return result
            model_class.model_validate(data)
            result["status"] = "valid"
        except Exception as e:  # noqa: BLE001
            # Intentionally broad: any YAML/Pydantic/IO error counts as
            # "invalid" so the validate command surfaces a useful message.
            result["status"] = "invalid"
            result["error"] = str(e)
        return result

    # Single task validation
    if args.task_name:
        task = args.task_name
        if task not in task_registry:
            print(
                f"Error: Unknown task '{task}'. Known tasks: {', '.join(sorted(task_registry.keys()))}",
                file=sys.stderr,
            )
            return 1
        pipeline_name, filename, model_class = task_registry[task]
        result = _validate_one(task, filename, model_class)
        if args.json_output:
            result["pipeline"] = pipeline_name
            print(json.dumps(result, indent=2))
        else:
            status = result["status"]
            symbol = {
                "valid": "OK",
                "invalid": "FAIL",
                "missing": "SKIP",
                "empty": "EMPTY",
            }[status]
            print(f"[{symbol}] {task} ({filename})")
            if result["error"]:
                print(f"  Error: {result['error']}")
        return 0 if result["status"] == "valid" else 1

    # Detect which pipeline(s) have outputs present
    detected = []
    for pipeline_name, steps, output_files, models in PIPELINES:
        present = [t for t, f in output_files.items() if (output_dir / f).exists()]
        if present:
            detected.append((pipeline_name, steps, output_files, models, present))

    if not detected:
        if args.json_output:
            print(json.dumps({"pipeline": None, "tasks": [], "next_step": None}))
        else:
            print(f"No task outputs found in {output_dir}")
        return 0

    all_valid = True
    all_results = []

    for pipeline_name, steps, output_files, models, present in detected:
        results = []
        for task_name in steps:
            if task_name not in output_files:
                continue
            filename = output_files[task_name]
            model_class = models[task_name]
            result = _validate_one(task_name, filename, model_class)
            result["pipeline"] = pipeline_name
            results.append(result)
            if result["status"] == "invalid":
                all_valid = False

        # Find next step
        resume = find_resume_step(output_dir, steps, output_files, models)

        # Cross-task referential integrity pass: only when multiple task
        # files exist (schema-only behavior is unchanged for a single file).
        from .cross_validate import CROSS_VALIDATORS, cross_validate

        cross_findings = []
        ran_cross = len(present) >= 2 and pipeline_name in CROSS_VALIDATORS
        if ran_cross:
            cross_findings = cross_validate(pipeline_name, output_dir)
            if any(f.severity == "error" for f in cross_findings):
                all_valid = False

        if args.json_output:
            all_results.append(
                {
                    "pipeline": pipeline_name,
                    "tasks": results,
                    "cross_task": [f.to_dict() for f in cross_findings],
                    "next_step": resume,
                }
            )
        else:
            print(f"\n=== {pipeline_name.upper()} pipeline ===")
            for r in results:
                status = r["status"]
                symbol = {
                    "valid": "OK",
                    "invalid": "FAIL",
                    "missing": "---",
                    "empty": "EMPTY",
                }[status]
                print(f"  [{symbol:>4}] {r['task']:8s} {r['file']}")
                if r["error"]:
                    # Truncate long validation errors
                    err = r["error"]
                    if len(err) > 200:
                        err = err[:200] + "..."
                    print(f"         {err}")
            if cross_findings:
                print("  Cross-task checks:")
                for f in cross_findings:
                    symbol = "ERR " if f.severity == "error" else "WARN"
                    print(f"  [{symbol}] {f.check}: {f.message}")
            elif ran_cross:
                print("  Cross-task checks: OK")
            if resume:
                print(f"  Next step: {resume}")
            else:
                print("  All tracked tasks valid.")

    if args.json_output:
        print(
            json.dumps(
                all_results if len(all_results) > 1 else all_results[0], indent=2
            )
        )

    return 0 if all_valid else 1


def deck_command(args: argparse.Namespace) -> int:
    """Handle the deck (slide-pipeline) command."""
    return _run_pipeline_command(
        args,
        default_output_dir="generated",
        steps=ALL_STEPS,
        output_files=TASK_OUTPUT_FILES,
        models=TASK_MODELS,
        make_run_config=SlideRunConfig.from_namespace,
        run_method="run_from",
        selection=("slides", "slides", parse_slide_selection),
        pass_force=True,
    )


def clean_source_command(args: argparse.Namespace) -> int:
    """Clean PDF artifacts from a source markdown file."""
    from .clean_source import CleaningConfig, clean_file, clean_source

    input_path = Path(args.input_file)
    if not input_path.is_file():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else None

    config = CleaningConfig(
        remove_toc=not args.keep_toc,
        remove_image_refs=not args.keep_images,
        remove_footnotes=not args.keep_footnotes,
        remove_page_numbers=not args.keep_page_numbers,
        unescape_chars=not args.keep_escapes,
    )

    if args.dry_run:
        text = input_path.read_text(encoding="utf-8")
        _, result = clean_source(text, config)
        print(f"Cleaning report for: {input_path}")
        print(f"  Original lines:        {result.original_lines}")
        print(f"  Cleaned lines:         {result.cleaned_lines}")
        print(
            f"  Lines removed:         {result.original_lines - result.cleaned_lines}"
        )
        print(f"  TOC lines removed:     {result.toc_lines_removed}")
        print(f"  Image refs removed:    {result.image_refs_removed}")
        print(f"  Footnote blocks:       {result.footnote_blocks_removed}")
        print(f"  Footnote superscripts: {result.footnote_refs_removed}")
        print(f"  Page numbers removed:  {result.page_numbers_removed}")
        print(f"  Escapes fixed:         {result.escapes_fixed}")
        return 0

    out_path, result = clean_file(input_path, output_path, config)
    print(f"Cleaned: {input_path} → {out_path}")
    print(
        f"  {result.original_lines} → {result.cleaned_lines} lines "
        f"({result.original_lines - result.cleaned_lines} removed)"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with all subcommands.

    Exposed separately from :func:`main` so tests can exercise the real
    argparse defaults together with preset resolution
    (:func:`presets.apply_presets`).
    """
    parser = argparse.ArgumentParser(
        prog="polyptych",
        description="Turn a source text into visual media: slide decks and single-page infographics",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Logger threshold (DEBUG/INFO/WARNING/ERROR). "
        "Defaults to $POLYPTYCH_LOG_LEVEL (deprecated alias: $SLIDE_GEN_LOG_LEVEL) or INFO.",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional path to also write logs to, in addition to stderr.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Deck (slide-pipeline) command.
    deck_parser = subparsers.add_parser(
        "deck",
        help="Run the slide deck generation pipeline",
    )
    deck_parser.add_argument(
        "source_file", type=str, help="Path to the source essay markdown file"
    )
    deck_parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=None,
        help="Output directory for generated files (default: ./generated/)",
    )
    deck_parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Override all LLM models for this run (ignores per-task config). Also settable via POLYPTYCH_MODEL env var (deprecated alias: SLIDE_GEN_MODEL).",
    )
    deck_parser.add_argument(
        "--from",
        dest="start",
        type=str,
        choices=["auto", *ALL_STEPS],
        default=None,
        help="Step to start from (default: auto, resumes from last valid output). Required input files must exist.",
    )
    deck_parser.add_argument(
        "--to",
        dest="end",
        type=str,
        choices=ALL_STEPS,
        default=None,
        help="Step to end at (default: images)",
    )
    _add_image_flags(deck_parser)
    _add_preset_flags(deck_parser)
    deck_parser.add_argument(
        "--slides",
        type=str,
        default=None,
        help="Specific slides to regenerate (e.g., '1,3' or '1-3' or '1-3,5,8-10'). Only applies to image generation step.",
    )
    deck_parser.add_argument(
        "--visuals-only",
        action="store_true",
        default=False,
        help="Generate images without any text elements (pure visuals)",
    )
    deck_parser.add_argument(
        "--style",
        type=str,
        default=None,
        help="Path to a style transfer prompt file (markdown) to customize visual style",
    )
    deck_parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Process Task 7 slides in batches of this size. Use 1 to process one slide at a time (most reliable for large presentations).",
    )
    deck_parser.add_argument(
        "--mode",
        type=str,
        choices=[
            "auto",
            "personal_essay",
            "analytical_critique",
            "policy_argument",
            "fiction",
            "strategic_diagnostic",
            "conceptual_essay",
        ],
        default=None,
        help="Override genre detection. 'auto' uses AI detection (default: auto)",
    )
    deck_parser.add_argument(
        "--interleave",
        type=int,
        default=None,
        metavar="N",
        help="(Deprecated: use --concurrent instead) "
        "Interleave prompt and image generation in chunks of N. "
        "Generates N prompts then N images, repeating until done. "
        "Implies per-slide prompt generation (batch-size 1).",
    )
    deck_parser.add_argument(
        "--concurrent",
        type=int,
        default=None,
        metavar="N",
        help="Run N concurrent image generation threads with producer-consumer "
        "architecture. Prompt generation starts immediately and images are "
        "generated as prompts become available.",
    )
    deck_parser.add_argument(
        "--producers",
        type=int,
        default=None,
        metavar="M",
        help="Number of concurrent prompt generation threads (default: min(N, 4)). "
        "Requires --concurrent.",
    )
    deck_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force regeneration of all items, ignoring existing prompt/image files. "
        "Only applies with --concurrent.",
    )
    _add_text_provider_args(deck_parser)
    _add_image_model_arg(deck_parser)

    # Infographic command
    info_parser = subparsers.add_parser(
        "infographic", help="Generate single-page infographic from source content"
    )
    info_parser.add_argument(
        "source_file", type=str, help="Path to the source markdown file"
    )
    info_parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=None,
        help="Output directory for generated files (default: ./infographic_output/)",
    )
    info_parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Override all LLM models for this run (ignores per-task config). Also settable via POLYPTYCH_MODEL env var (deprecated alias: SLIDE_GEN_MODEL).",
    )
    info_parser.add_argument(
        "--variants",
        "-n",
        type=int,
        default=None,
        choices=range(1, 6),
        metavar="N",
        help="Number of infographic prompt variants to generate (1-5, default: 3)",
    )
    _add_image_flags(info_parser)
    _add_preset_flags(info_parser)
    info_parser.add_argument(
        "--style",
        type=str,
        default="prompts/style-transfer/infographic/semi-flat-vector.md",
        help="Path to a style transfer prompt file (markdown) to customize visual style (default: semi-flat-vector)",
    )
    info_parser.add_argument(
        "--skip-images",
        action="store_true",
        default=False,
        help="Skip image generation, only generate prompts",
    )
    info_parser.add_argument(
        "--critique",
        action="store_true",
        default=False,
        help="Enable the critique-refine loop for I2 prompts (audits entity/color "
        "consistency, content coverage, flow, and text density before image "
        "generation). Off by default.",
    )
    info_parser.add_argument(
        "--critique-rounds",
        type=int,
        default=None,
        metavar="N",
        help="Number of critique-refine iterations for I2 (default: 1). "
        "Requires --critique.",
    )
    info_parser.add_argument(
        "--from",
        dest="start",
        type=str,
        choices=["auto", *INFOGRAPHIC_STEPS],
        default=None,
        help="Step to start from (default: auto, resumes from last valid output). Steps: i0 (analysis), i1 (design), i2 (prompts), images.",
    )
    info_parser.add_argument(
        "--to",
        dest="end",
        type=str,
        choices=INFOGRAPHIC_STEPS,
        default=None,
        help="Step to end at (default: images)",
    )
    _add_text_provider_args(info_parser)
    _add_image_model_arg(info_parser)

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate task YAML outputs against Pydantic schemas"
    )
    validate_parser.add_argument(
        "output_dir", type=str, help="Path to the output directory to validate"
    )
    validate_parser.add_argument(
        "task_name",
        type=str,
        nargs="?",
        default=None,
        help="Specific task to validate (e.g., task1, n0, i2). If omitted, validates all.",
    )
    validate_parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        default=False,
        help="Output results as JSON for programmatic parsing",
    )

    # Clean-source command
    clean_parser = subparsers.add_parser(
        "clean-source", help="Clean PDF artifacts from a source markdown file"
    )
    clean_parser.add_argument(
        "input_file", type=str, help="Path to the markdown file to clean"
    )
    clean_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: <stem>-clean.md)",
    )
    clean_parser.add_argument(
        "--keep-toc", action="store_true", help="Keep table of contents"
    )
    clean_parser.add_argument(
        "--keep-images", action="store_true", help="Keep image references"
    )
    clean_parser.add_argument(
        "--keep-footnotes", action="store_true", help="Keep footnotes"
    )
    clean_parser.add_argument(
        "--keep-page-numbers", action="store_true", help="Keep standalone page numbers"
    )
    clean_parser.add_argument(
        "--keep-escapes", action="store_true", help="Keep backslash escaping"
    )
    clean_parser.add_argument(
        "--dry-run", action="store_true", help="Print report without writing"
    )

    return parser


def main() -> int:
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args()

    # Wire the polyptych logger before any subcommand runs. ``force=True`` so
    # a CLI flag overrides any inherited configuration (e.g. from tests).
    configure_logging(level=args.log_level, log_file=args.log_file, force=True)

    if args.command is None:
        parser.print_help()
        return 0

    # Deprecation warning for --interleave when --concurrent would be better
    import warnings

    if hasattr(args, "interleave") and args.interleave is not None:
        if not (hasattr(args, "concurrent") and args.concurrent is not None):
            warnings.warn(
                "--interleave is deprecated and will be removed in a future version. "
                "Use --concurrent N for parallel image generation instead.",
                DeprecationWarning,
                stacklevel=1,
            )
            print(
                "WARNING: --interleave is deprecated. Use --concurrent N instead.",
                file=sys.stderr,
            )

    # Resolve --image-preset / --pipeline-preset before any handler reads
    # provider/size/aspect_ratio/etc. Explicit user flags always win; presets
    # only fill attributes the user did not pass.
    pipeline_name = _SUBCOMMAND_TO_PIPELINE.get(args.command)
    if pipeline_name is not None:
        try:
            presets.apply_presets(
                args,
                pipeline=pipeline_name,
                image_preset=getattr(args, "image_preset", None),
                pipeline_preset=getattr(args, "pipeline_preset", None),
            )
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    # Validate concurrency flags AFTER preset resolution so that values
    # supplied by a pipeline preset (e.g. producers without concurrent) are
    # caught the same way as explicit flags.
    if (
        hasattr(args, "interleave")
        and args.interleave is not None
        and args.interleave <= 0
    ):
        print("Error: --interleave must be a positive integer", file=sys.stderr)
        return 1

    if (
        hasattr(args, "concurrent")
        and args.concurrent is not None
        and args.concurrent <= 0
    ):
        print("Error: --concurrent must be a positive integer", file=sys.stderr)
        return 1

    if hasattr(args, "producers") and args.producers is not None:
        if not hasattr(args, "concurrent") or args.concurrent is None:
            print("Error: --producers requires --concurrent", file=sys.stderr)
            return 1
        if args.producers <= 0:
            print("Error: --producers must be a positive integer", file=sys.stderr)
            return 1

    if args.command == "deck":
        return deck_command(args)

    if args.command == "infographic":
        return infographic_command(args)

    if args.command == "validate":
        return validate_command(args)

    if args.command == "clean-source":
        return clean_source_command(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
