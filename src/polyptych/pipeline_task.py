"""Task (slide) pipeline mixin.

The original 7-task slide-deck generation pipeline. Tasks 1–7 plus
image generation, with optional batched, interleaved, and concurrent
execution modes.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

from .models import (
    ImagePrompt,
    SlideImagePrompt,
    Task1Output,
    Task2Output,
    Task3Output,
    Task4Output,
    Task5Output,
    Task6Output,
    Task7Output,
)
from .pipeline_base import IMAGE_GEN_AVAILABLE, PipelineMixin
from .pipeline_config import (
    ALL_STEPS,
    STEP_DEPENDENCIES,
    StepName,
    TASK_MODELS,
    TASK_OUTPUT_FILES,
    _make_step_logger,
)
from .image_batch import (
    BatchItem,
    BatchSettings,
    BuiltPrompt,
    ImageBatchGenerator,
)
from .run_config import SlideRunConfig
from .tasks import (
    run_task_01,
    run_task_02,
    run_task_03,
    run_task_04,
    run_task_05,
    run_task_06,
    run_task_07,
    run_task_07_single_slide,
)

if TYPE_CHECKING:
    from pixbridge.models import ImagePrompt as ImageGenPrompt
else:
    # Image generation prompt model — only used inside image-generation methods.
    try:
        from pixbridge.models import ImagePrompt as ImageGenPrompt
    except ImportError:
        pass


class SlidePipelineTaskMixin(PipelineMixin):
    """Mixin holding the 7-task slide-pipeline methods for SlidePipeline."""

    def _load_task_output(self, task_name: str) -> bool:
        """Load a slide task output from its saved YAML file.

        Thin wrapper over ``_load_task_output_generic``. The slide pipeline's
        task names already start with ``task`` (``task1`` … ``task7``), so the
        attribute stored is ``self.{task_name}_output`` with no extra prefix.
        """
        return self._load_task_output_generic(
            task_name,
            output_files=TASK_OUTPUT_FILES,
            models=TASK_MODELS,
            attr_prefix="",
        )

    def _load_dependencies(self, step: StepName) -> None:
        """Load all required dependencies for a slide step.

        Raises:
            FileNotFoundError: If a required dependency file is missing.
        """
        self._load_dependencies_generic(
            step,
            step_deps=STEP_DEPENDENCIES,
            output_files=TASK_OUTPUT_FILES,
            models=TASK_MODELS,
            pipeline_label="slide",
            attr_prefix="",
        )

    def run_task1(self, mode_override: str | None = None) -> Task1Output:
        """Run Task 1: Genre Classification.

        Args:
            mode_override: If provided (and not "auto"), forces the genre to this value.
        """
        log = _make_step_logger("task1")
        log("Running Task 1: Genre Classification...")
        if mode_override and mode_override != "auto":
            log(f"  Mode override: {mode_override}")
        self.task1_output = run_task_01(
            source_essay=self.source_essay,
            client=self.text_client,
            model=self._model_for("task1"),
            mode_override=mode_override,
        )
        self._save_yaml(self.task1_output.model_dump(), TASK_OUTPUT_FILES["task1"])
        log(
            f"  Genre: {self.task1_output.genre} (confidence: {self.task1_output.confidence:.2f})"
        )
        return self.task1_output

    def run_task2(self) -> Task2Output:
        """Run Task 2: Source Analysis."""
        if self.task1_output is None:
            raise ValueError(
                "Task 1 output required. Run task1 first or load from file."
            )

        log = _make_step_logger("task2")
        log("Running Task 2: Source Analysis...")
        self.task2_output = run_task_02(
            source_essay=self.source_essay,
            task1_output=self.task1_output,
            client=self.text_client,
            model=self._model_for("task2"),
        )
        self._save_yaml(self.task2_output.model_dump(), TASK_OUTPUT_FILES["task2"])
        log(f"  Sections: {len(self.task2_output.structural_analysis.sections)}")
        log(f"  Quotable passages: {len(self.task2_output.quotable_passages)}")
        return self.task2_output

    def run_task3(self) -> Task3Output:
        """Run Task 3: Structure Planning."""
        if self.task1_output is None or self.task2_output is None:
            raise ValueError("Tasks 1-2 outputs required.")

        log = _make_step_logger("task3")
        log("Running Task 3: Structure Planning...")
        self.task3_output = run_task_03(
            task1_output=self.task1_output,
            task2_output=self.task2_output,
            client=self.text_client,
            model=self._model_for("task3"),
        )
        self._save_yaml(self.task3_output.model_dump(), TASK_OUTPUT_FILES["task3"])
        log(f"  Slide count: {self.task3_output.slide_count}")
        log(f"  Arc type: {self.task3_output.arc_visualization.type}")
        return self.task3_output

    def run_task4(self) -> Task4Output:
        """Run Task 4: Content Allocation."""
        if (
            self.task1_output is None
            or self.task2_output is None
            or self.task3_output is None
        ):
            raise ValueError("Tasks 1-3 outputs required.")

        log = _make_step_logger("task4")
        log("Running Task 4: Content Allocation...")
        self.task4_output = run_task_04(
            source_essay=self.source_essay,
            task1_output=self.task1_output,
            task2_output=self.task2_output,
            task3_output=self.task3_output,
            client=self.text_client,
            model=self._model_for("task4"),
        )
        self._save_yaml(self.task4_output.model_dump(), TASK_OUTPUT_FILES["task4"])
        log(f"  Allocations: {len(self.task4_output.allocations)}")
        return self.task4_output

    def run_task5(self, style_prompt: str | None = None) -> Task5Output:
        """Run Task 5: Visual Design Specification."""
        if (
            self.task1_output is None
            or self.task2_output is None
            or self.task4_output is None
        ):
            raise ValueError("Tasks 1, 2, and 4 outputs required.")

        log = _make_step_logger("task5")
        log("Running Task 5: Visual Design Specification...")
        self.task5_output = run_task_05(
            task1_output=self.task1_output,
            task2_output=self.task2_output,
            task4_output=self.task4_output,
            client=self.text_client,
            model=self._model_for("task5"),
            style_prompt=style_prompt,
        )
        self._save_yaml(self.task5_output.model_dump(), TASK_OUTPUT_FILES["task5"])
        log(f"  Motif type: {self.task5_output.design_system.motif.type}")
        log(
            f"  Primary accent: {self.task5_output.design_system.color_palette.primary_accent}"
        )
        return self.task5_output

    def run_task6(self) -> Task6Output:
        """Run Task 6: Slide Specification."""
        if (
            self.task1_output is None
            or self.task2_output is None
            or self.task3_output is None
            or self.task4_output is None
            or self.task5_output is None
        ):
            raise ValueError("Tasks 1-5 outputs required.")

        log = _make_step_logger("task6")
        log("Running Task 6: Slide Specification...")
        log(f"  Genre: {self.task1_output.genre}")
        self.task6_output = run_task_06(
            task1_output=self.task1_output,
            task2_output=self.task2_output,
            task3_output=self.task3_output,
            task4_output=self.task4_output,
            task5_output=self.task5_output,
            client=self.text_client,
            model=self._model_for("task6"),
        )
        self._save_yaml(self.task6_output.model_dump(), TASK_OUTPUT_FILES["task6"])
        log(f"  Slides specified: {len(self.task6_output.slides)}")
        return self.task6_output

    def run_task7(
        self,
        visuals_only: bool = False,
        style_prompt: str | None = None,
        batch_size: int | None = None,
        provider: str = "gemini",
    ) -> Task7Output:
        """Run Task 7: Image Prompt Generation.

        Args:
            visuals_only: If True, generate prompts without text elements.
            style_prompt: Optional style transfer prompt to customize visual style.
            batch_size: If specified, process slides in batches of this size.
                       Use batch_size=1 to process one slide at a time (most reliable).
                       If None, all slides are processed in a single API call.
            provider: Target image generation provider for prompt optimization.
        """
        if (
            self.task1_output is None
            or self.task5_output is None
            or self.task6_output is None
        ):
            raise ValueError("Tasks 1, 5, and 6 outputs required.")

        log = _make_step_logger("task7")
        log("Running Task 7: Image Prompt Generation...")
        character_canon = self._character_canon()
        if character_canon:
            log(f"  Character canon: {len(character_canon)} locked identities")
        if visuals_only:
            log("  Mode: visuals-only (no text elements)")
        if style_prompt:
            log("  Mode: custom style transfer")
        if provider != "gemini":
            log(f"  Provider optimization: {provider}")

        if batch_size is not None:
            # Process slides in batches
            log(f"  Batch size: {batch_size}")
            self.task7_output = self._run_task7_batched(
                visuals_only=visuals_only,
                style_prompt=style_prompt,
                batch_size=batch_size,
                provider=provider,
            )
        else:
            # Process all slides in a single call
            self.task7_output = run_task_07(
                task1_output=self.task1_output,
                task5_output=self.task5_output,
                task6_output=self.task6_output,
                client=self.text_client,
                model=self._model_for("task7"),
                visuals_only=visuals_only,
                style_prompt=style_prompt,
                provider=provider,
                max_output_tokens=self._max_tokens_for("task7"),
                character_canon=character_canon,
            )

        # Stamp the provider the prompts were tuned for (overwrites anything
        # the LLM may have put in the field).
        self.task7_output.prompt_provider = provider
        self._save_yaml(self.task7_output.model_dump(), TASK_OUTPUT_FILES["task7"])

        # Also save individual slide prompts
        for slide_prompt in self.task7_output.slide_prompts:
            filename = f"slide-{slide_prompt.slide_number:02d}-prompt.yaml"
            self._save_yaml(
                slide_prompt.image_prompt.model_dump(),
                f"prompts/{filename}",
            )

        log(f"  Image prompts generated: {len(self.task7_output.slide_prompts)}")
        return self.task7_output

    def _character_canon(self):
        """Canonical fiction character sheets from task2, when present.

        task2 is a *soft* dependency of task7: when resuming from task7/images
        it is loaded opportunistically here, so legacy output dirs without
        task2-analysis.yaml keep working (canon is optional — ``None`` for
        non-fiction sources and legacy task2 outputs).
        """
        task2 = getattr(self, "task2_output", None)
        if task2 is None:
            self._load_task_output("task2")
            task2 = getattr(self, "task2_output", None)
        return getattr(task2, "character_canon", None)

    def _slide_prompt_generator(
        self,
        visuals_only: bool = False,
        style_prompt: str | None = None,
        provider: str = "gemini",
    ) -> Generator[SlideImagePrompt, None, None]:
        """Yield SlideImagePrompt objects one at a time.

        Each individual prompt YAML is saved to disk before yielding.
        Uses per-slide LLM calls (same as batch_size=1).
        """
        assert self.task6_output is not None, (
            "task6 output must be loaded before generating slide prompts"
        )
        assert self.task1_output is not None, (
            "task1 output must be loaded before generating slide prompts"
        )
        assert self.task5_output is not None, (
            "task5 output must be loaded before generating slide prompts"
        )
        slides = self.task6_output.slides
        total_slides = len(slides)
        title = slides[0].content.headline if slides else "Untitled"
        character_canon = self._character_canon()

        for slide in slides:
            slide_prompt = run_task_07_single_slide(
                slide_spec=slide.model_dump(),
                task1_output=self.task1_output,
                task5_output=self.task5_output,
                slide_number=slide.number,
                total_slides=total_slides,
                title=title,
                client=self.text_client,
                model=self._model_for("task7"),
                visuals_only=visuals_only,
                style_prompt=style_prompt,
                provider=provider,
                character_canon=character_canon,
            )

            # Save individual prompt YAML
            filename = f"slide-{slide_prompt.slide_number:02d}-prompt.yaml"
            self._save_yaml(
                slide_prompt.image_prompt.model_dump(),
                f"prompts/{filename}",
            )

            yield slide_prompt

    def _run_task7_batched(
        self,
        visuals_only: bool,
        style_prompt: str | None,
        batch_size: int,
        provider: str = "gemini",
    ) -> Task7Output:
        """Process Task 7 in batches to avoid output token limits.

        Delegates to _slide_prompt_generator and collects all results.
        """
        all_prompts = list(
            self._slide_prompt_generator(
                visuals_only=visuals_only,
                style_prompt=style_prompt,
                provider=provider,
            )
        )
        return Task7Output(slide_prompts=all_prompts)

    @staticmethod
    def _slide_batch_items(prompts: list[SlideImagePrompt]) -> list[BatchItem]:
        """Wrap slide prompts as batch items keyed by slide number."""
        return [
            BatchItem(
                index=p.slide_number,
                item_id=f"slide-{p.slide_number:02d}",
                payload=p,
            )
            for p in prompts
        ]

    def _slide_image_batch(
        self,
        provider: str,
        size: str | None,
        aspect_ratio: str,
        quality: str | None,
        image_model: str | None,
    ) -> ImageBatchGenerator:
        """Compose the shared image-batch engine for slide prompts."""

        def build(slide_prompt: SlideImagePrompt) -> BuiltPrompt:
            prompt_data = slide_prompt.image_prompt.model_dump()
            return BuiltPrompt(ImageGenPrompt.model_validate(prompt_data))

        return ImageBatchGenerator(
            client_factory=lambda: self._make_image_client(provider),
            failure_sink=self.image_failures,
            images_dir=self.output_dir / "images",
            label="slide",
            build_prompt=build,
            settings=BatchSettings(
                size=size,
                aspect_ratio=aspect_ratio,
                quality=quality,
                image_model=image_model,
            ),
        )

    def _warn_on_prompt_provider_mismatch(self, actual_provider: str) -> None:
        """Warn when task7 prompts were tuned for a different image provider.

        Task7 bakes provider-specific guidelines
        (``prompts/providers/<provider>-best-practices.md``) into the prompts
        at text-task time. Resuming with ``--from images`` and a different
        provider silently degrades quality, so name both providers and point
        at the fix. ``prompt_provider`` is ``None`` for output dirs that
        predate provider recording — nothing to compare then.
        """
        recorded = getattr(self.task7_output, "prompt_provider", None)
        if recorded is not None and recorded != actual_provider:
            log = _make_step_logger("images")
            log(
                f"WARNING: task7 prompts were tuned for image provider "
                f"'{recorded}' but images are being generated with "
                f"'{actual_provider}'. Provider-specific guidance baked into "
                f"the prompts may not fit. For best results re-run task7: "
                f"--from task7 --provider {actual_provider}"
            )

    def run_images(
        self,
        provider: str = "gemini",
        size: str | None = None,
        aspect_ratio: str = "16:9",
        quality: str | None = None,
        image_model: str | None = None,
        slides: list[int] | None = None,
    ) -> list[Path]:
        """Generate images from Task 7 prompts.

        Args:
            provider: Image generation provider (gemini, openai, xai).
            size: Size preset for output images. Provider-specific defaults if not specified.
            aspect_ratio: Aspect ratio for output images.
            quality: Quality level (OpenAI only: low, medium, high).
            image_model: Model to use for image generation. Provider-specific default if not specified.
            slides: Optional list of slide numbers to regenerate. If None, all slides are generated.

        Returns:
            List of paths to generated images.
        """
        if not IMAGE_GEN_AVAILABLE:
            raise ImportError(
                "pixbridge package not available. "
                "Make sure it's installed in the same environment."
            )

        if self.task7_output is None:
            raise ValueError("Task 7 output required.")

        log = _make_step_logger("images")
        log(f"Generating images with {provider}...")
        self._warn_on_prompt_provider_mismatch(provider)

        # Filter to specific slides if requested
        prompts_to_process = self.task7_output.slide_prompts
        if slides:
            prompts_to_process = [
                p for p in prompts_to_process if p.slide_number in slides
            ]
            log(
                f"  Processing {len(prompts_to_process)} of {len(self.task7_output.slide_prompts)} slides: {slides}"
            )

        batch = self._slide_image_batch(
            provider, size, aspect_ratio, quality, image_model
        )
        result = batch.run_sequential(self._slide_batch_items(prompts_to_process))
        batch.report(result)
        return result.generated

    def _run_slides_interleaved(
        self,
        interleave: int,
        visuals_only: bool = False,
        style_prompt: str | None = None,
        provider: str = "gemini",
        size: str | None = None,
        aspect_ratio: str = "16:9",
        quality: str | None = None,
        image_model: str | None = None,
        slides: list[int] | None = None,
    ) -> None:
        """Run slide prompt and image generation interleaved in chunks.

        Generates N prompts, then N images, then next N prompts, etc.
        Uses per-slide LLM calls (batch_size=1 semantics).
        """
        if not IMAGE_GEN_AVAILABLE:
            raise ImportError(
                "pixbridge package not available. "
                "Make sure it's installed in the same environment."
            )

        if (
            self.task1_output is None
            or self.task5_output is None
            or self.task6_output is None
        ):
            raise ValueError("Tasks 1, 5, and 6 outputs required.")

        log = _make_step_logger("images")
        log(f"Running slide pipeline interleaved (chunk size: {interleave})")

        gen = self._slide_prompt_generator(
            visuals_only=visuals_only,
            style_prompt=style_prompt,
            provider=provider,
        )
        items = (
            BatchItem(
                index=p.slide_number,
                item_id=f"slide-{p.slide_number:02d}",
                payload=p,
            )
            for p in gen
        )

        batch = self._slide_image_batch(
            provider, size, aspect_ratio, quality, image_model
        )
        # Slides outside the filter still get their prompts collected (so the
        # aggregate Task7Output stays complete) but produce no image.
        select = (lambda item: item.index in slides) if slides else None
        all_prompts, result = batch.run_interleaved(
            items, chunk_size=interleave, select=select
        )

        # Save aggregate Task7Output
        self.task7_output = Task7Output(
            slide_prompts=all_prompts, prompt_provider=provider
        )
        self._save_yaml(self.task7_output.model_dump(), TASK_OUTPUT_FILES["task7"])

        log(f"  Total prompts generated: {len(all_prompts)}")
        log(f"  Total images generated: {len(result.generated)}")

        if result.failed:
            log(f"WARNING: {len(result.failed)} image(s) failed to generate:")
            for num, err in result.failed:
                log(f"  - Slide {num}: {err}")

    def _run_images_concurrent(
        self,
        num_consumers: int,
        provider: str = "gemini",
        size: str | None = None,
        aspect_ratio: str = "16:9",
        quality: str | None = None,
        image_model: str | None = None,
        slides: list[int] | None = None,
        force: bool = False,
    ) -> None:
        """Run image generation concurrently when prompts already exist on disk.

        Prompts are pre-loaded, so producers are no-ops; only the image
        generation (consumer side) benefits from parallelism.
        """
        if not IMAGE_GEN_AVAILABLE:
            raise ImportError("pixbridge package not available.")

        if self.task7_output is None:
            raise ValueError("Task 7 output required for image generation.")

        self._warn_on_prompt_provider_mismatch(provider)

        batch = self._slide_image_batch(
            provider, size, aspect_ratio, quality, image_model
        )

        prompts = [
            p
            for p in self.task7_output.slide_prompts
            if not slides or p.slide_number in slides
        ]
        work_items, skipped = batch.build_preloaded_work_items(
            self._slide_batch_items(prompts), force=force
        )

        if not batch.log_resume(work_items, skipped):
            return

        batch.log(f"Running slide images concurrent (consumers={num_consumers})")
        batch.run_concurrent(work_items, num_consumers=num_consumers)

    def _run_slides_concurrent(
        self,
        num_producers: int,
        num_consumers: int,
        visuals_only: bool = False,
        style_prompt: str | None = None,
        provider: str = "gemini",
        size: str | None = None,
        aspect_ratio: str = "16:9",
        quality: str | None = None,
        image_model: str | None = None,
        slides: list[int] | None = None,
        force: bool = False,
    ) -> None:
        """Run slide prompt + image generation concurrently via producer-consumer engine."""
        if not IMAGE_GEN_AVAILABLE:
            raise ImportError("pixbridge package not available.")

        if (
            self.task1_output is None
            or self.task5_output is None
            or self.task6_output is None
        ):
            raise ValueError("Tasks 1, 5, and 6 outputs required.")

        from .concurrent_engine import WorkItem

        all_slides = self.task6_output.slides
        total_slides = len(all_slides)
        title = all_slides[0].content.headline if all_slides else "Untitled"

        batch = self._slide_image_batch(
            provider, size, aspect_ratio, quality, image_model
        )

        specs = [
            BatchItem(
                index=s.number,
                item_id=f"slide-{s.number:02d}",
                payload=s.model_dump(),
            )
            for s in all_slides
            if not slides or s.number in slides
        ]

        def parse_prompt(loaded: dict, index: int) -> SlideImagePrompt:
            return SlideImagePrompt(
                slide_number=index,
                image_prompt=ImagePrompt.model_validate(loaded),
            )

        work_items, skipped, preloaded, from_scratch = batch.build_resumable_work_items(
            specs,
            force=force,
            load_yaml=self._load_yaml,
            parse_prompt=parse_prompt,
        )

        if not batch.log_resume(work_items, skipped, preloaded, from_scratch):
            return

        batch.log(
            f"Running slide pipeline concurrent (producers={num_producers}, consumers={num_consumers})"
        )

        # Capture shared read-only state for closures
        task1 = self.task1_output
        task5 = self.task5_output
        text_client = self.text_client
        model = self._model_for("task7")
        character_canon = self._character_canon()

        def produce(item: WorkItem) -> None:
            if item.prompt is not None:
                return  # Pre-loaded from disk, skip LLM call
            slide_prompt = run_task_07_single_slide(
                slide_spec=item.input_data,
                task1_output=task1,
                task5_output=task5,
                slide_number=item.index,
                total_slides=total_slides,
                title=title,
                client=text_client,
                model=model,
                visuals_only=visuals_only,
                style_prompt=style_prompt,
                provider=provider,
                character_canon=character_canon,
            )
            # Save prompt YAML
            filename = f"slide-{slide_prompt.slide_number:02d}-prompt.yaml"
            self._save_yaml(
                slide_prompt.image_prompt.model_dump(), f"prompts/{filename}"
            )
            item.prompt = slide_prompt

        batch.run_concurrent(
            work_items,
            num_consumers=num_consumers,
            num_producers=num_producers,
            produce_fn=produce,
        )

        # Collect prompts from completed + failed for aggregate YAML
        all_prompts = [item.prompt for item in work_items if item.prompt is not None]
        if all_prompts:
            self.task7_output = Task7Output(
                slide_prompts=all_prompts, prompt_provider=provider
            )
            self._save_yaml(self.task7_output.model_dump(), TASK_OUTPUT_FILES["task7"])

    def run_from(self, config: SlideRunConfig) -> None:
        """Run pipeline from a specific step to another step.

        Loads required outputs from previous steps if they exist as files.
        Step range comes from ``config.from_step`` and ``config.to_step``.
        """
        start_step: StepName = config.from_step  # type: ignore[assignment]
        end_step: StepName = config.to_step  # type: ignore[assignment]
        provider = config.provider
        size = config.size
        aspect_ratio = config.aspect_ratio
        quality = config.quality
        image_model = config.image_model
        slides = config.slides
        visuals_only = config.visuals_only
        style_prompt_path = config.style_prompt_path
        batch_size = config.batch_size
        mode = config.mode
        interleave = config.interleave
        concurrent = config.concurrent
        num_producers = config.num_producers
        force = config.force
        ref_images = config.ref_images
        output_format = config.output_format
        output_compression = config.output_compression

        image_model = image_model or self._image_model_for(provider)

        self._set_image_run_defaults(
            ref_images=ref_images,
            output_format=output_format,
            output_compression=output_compression,
        )

        if end_step is None:
            end_step = "images"

        start_idx = ALL_STEPS.index(start_step)
        end_idx = ALL_STEPS.index(end_step)

        if start_idx > end_idx:
            raise ValueError(
                f"Start step '{start_step}' comes after end step '{end_step}'"
            )

        print(f"Running pipeline: {start_step} -> {end_step}")
        print(f"  Source: {self.source_path}")
        print(f"  Output: {self.output_dir}")
        print()

        # Determine all steps to run
        steps_to_run = ALL_STEPS[start_idx : end_idx + 1]

        # Load dependencies for ALL steps that will be run (not just start step)
        # Exclude steps that will be regenerated during this run
        print("Loading dependencies...")
        all_deps: set[str] = set()
        for step in steps_to_run:
            for dep in STEP_DEPENDENCIES[step]:
                if dep not in steps_to_run:
                    all_deps.add(dep)

        missing = []
        for dep in sorted(all_deps):
            if not self._load_task_output(dep):
                missing.append(dep)

        if missing:
            missing_files = [
                f"{self.output_dir / TASK_OUTPUT_FILES[d]}" for d in missing
            ]
            raise FileNotFoundError(
                f"Cannot run {start_step}->{end_step}: missing required outputs: {', '.join(missing)}\n"
                f"Expected files:\n  " + "\n  ".join(missing_files)
            )

        # Load style prompt if provided
        style_prompt = None
        if style_prompt_path:
            style_path = Path(style_prompt_path)
            if not style_path.exists():
                raise FileNotFoundError(
                    f"Style prompt file not found: {style_prompt_path}"
                )
            style_prompt = style_path.read_text()
            print(f"Loaded style prompt from: {style_prompt_path}")

        # Check if concurrent mode applies: full (task7+images) or images-only
        use_concurrent_full = (
            concurrent is not None
            and "task7" in steps_to_run
            and "images" in steps_to_run
        )
        use_concurrent_images_only = (
            concurrent is not None
            and not use_concurrent_full
            and "images" in steps_to_run
            and "task7" not in steps_to_run
        )
        use_concurrent = use_concurrent_full or use_concurrent_images_only

        # Check if interleaved mode applies: both task7 and images in range
        use_interleaved = (
            not use_concurrent
            and interleave is not None
            and "task7" in steps_to_run
            and "images" in steps_to_run
        )

        if interleave is not None and not use_interleaved and not use_concurrent:
            if "task7" not in steps_to_run:
                print(
                    "  Note: --interleave ignored because task7 is not in the step range"
                )
            if "images" not in steps_to_run:
                print(
                    "  Note: --interleave ignored because images step is not in the step range"
                )

        if concurrent is not None and not use_concurrent:
            if "images" not in steps_to_run:
                print(
                    "  Note: --concurrent ignored because images step is not in the step range"
                )

        # When interleaving, imply batch_size=1 if not explicitly set
        if use_interleaved and batch_size is None:
            batch_size = 1

        print()
        if use_concurrent_full:
            # use_concurrent_full implies concurrent is set.
            assert concurrent is not None
            _num_producers = (
                num_producers if num_producers is not None else min(concurrent, 4)
            )
            # Run steps before task7 normally
            for step in steps_to_run:
                if step in ("task7", "images"):
                    continue
                if step == "task1":
                    self.run_task1(mode_override=mode)
                elif step == "task5":
                    self.run_task5(style_prompt=style_prompt)
                else:
                    method = getattr(self, f"run_{step}")
                    method()

            # Run concurrent task7+images
            self._run_slides_concurrent(
                num_producers=_num_producers,
                num_consumers=concurrent,
                visuals_only=visuals_only,
                style_prompt=style_prompt,
                provider=provider,
                size=size,
                aspect_ratio=aspect_ratio,
                quality=quality,
                image_model=image_model,
                slides=slides,
                force=force,
            )
        elif use_concurrent_images_only:
            # use_concurrent_images_only implies concurrent is set.
            assert concurrent is not None
            # Run any non-image steps normally first
            for step in steps_to_run:
                if step == "images":
                    continue
                if step == "task1":
                    self.run_task1(mode_override=mode)
                elif step == "task7":
                    self.run_task7(
                        visuals_only=visuals_only,
                        style_prompt=style_prompt,
                        batch_size=batch_size,
                        provider=provider,
                    )
                elif step == "task5":
                    self.run_task5(style_prompt=style_prompt)
                else:
                    method = getattr(self, f"run_{step}")
                    method()

            # Run images-only concurrent
            self._run_images_concurrent(
                num_consumers=concurrent,
                provider=provider,
                size=size,
                aspect_ratio=aspect_ratio,
                quality=quality,
                image_model=image_model,
                slides=slides,
                force=force,
            )
        elif use_interleaved:
            # use_interleaved implies interleave is set.
            assert interleave is not None
            # Run steps before task7 normally
            for step in steps_to_run:
                if step in ("task7", "images"):
                    continue
                if step == "task1":
                    self.run_task1(mode_override=mode)
                elif step == "task5":
                    self.run_task5(style_prompt=style_prompt)
                else:
                    method = getattr(self, f"run_{step}")
                    method()

            # Run interleaved task7+images
            self._run_slides_interleaved(
                interleave=interleave,
                visuals_only=visuals_only,
                style_prompt=style_prompt,
                provider=provider,
                size=size,
                aspect_ratio=aspect_ratio,
                quality=quality,
                image_model=image_model,
                slides=slides,
            )
        else:
            for step in steps_to_run:
                if step == "images":
                    self.run_images(
                        provider=provider,
                        size=size,
                        aspect_ratio=aspect_ratio,
                        quality=quality,
                        image_model=image_model,
                        slides=slides,
                    )
                elif step == "task7":
                    self.run_task7(
                        visuals_only=visuals_only,
                        style_prompt=style_prompt,
                        batch_size=batch_size,
                        provider=provider,
                    )
                elif step == "task1":
                    self.run_task1(mode_override=mode)
                elif step == "task5":
                    self.run_task5(style_prompt=style_prompt)
                else:
                    method = getattr(self, f"run_{step}")
                    method()

        self._write_manifest("slide", config)

        print()
        print("Pipeline complete!")

    def run_full_pipeline(
        self,
        skip_images: bool = False,
        provider: str = "gemini",
        size: str | None = None,
        aspect_ratio: str = "16:9",
        quality: str | None = None,
    ) -> None:
        """Run the full pipeline from task1 to images."""
        to_step = "task7" if skip_images else "images"
        self.run_from(
            SlideRunConfig(
                from_step="task1",
                to_step=to_step,
                provider=provider,
                size=size,
                aspect_ratio=aspect_ratio,
                quality=quality,
            )
        )
