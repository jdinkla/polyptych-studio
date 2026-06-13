"""Infographic pipeline mixin.

Generates one or more infographic images from source content. Three
text steps (i0 content analysis → i1 design spec → i2 image prompts)
followed by image generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from .image_batch import (
    BatchItem,
    BatchSettings,
    BuiltPrompt,
    ImageBatchGenerator,
)
from .models import TaskI0Output, TaskI1Output, TaskI2Output
from .pipeline_base import IMAGE_GEN_AVAILABLE, PipelineMixin
from .pipeline_config import (
    INFOGRAPHIC_MODELS,
    INFOGRAPHIC_OUTPUT_FILES,
    INFOGRAPHIC_STEP_DEPENDENCIES,
    INFOGRAPHIC_STEPS,
    InfographicStepName,
    _make_step_logger,
)
from .run_config import InfographicRunConfig
from .tasks import (
    run_task_i0,
    run_task_i1,
    run_task_i2,
    run_task_i2_critique,
    run_task_i2_refine,
)


class SlidePipelineInfographicMixin(PipelineMixin):
    """Mixin holding infographic-pipeline methods for SlidePipeline."""

    def _load_infographic_task_output(self, task_name: str) -> bool:
        """Load an infographic task output from its saved YAML file.

        Thin wrapper over ``_load_task_output_generic`` with the infographic
        output/model maps bound.
        """
        return self._load_task_output_generic(
            task_name,
            output_files=INFOGRAPHIC_OUTPUT_FILES,
            models=INFOGRAPHIC_MODELS,
        )

    def _load_infographic_dependencies(self, step: InfographicStepName) -> None:
        """Load all required dependencies for an infographic step.

        Raises:
            FileNotFoundError: If a required dependency file is missing.
        """
        self._load_dependencies_generic(
            step,
            step_deps=INFOGRAPHIC_STEP_DEPENDENCIES,
            output_files=INFOGRAPHIC_OUTPUT_FILES,
            models=INFOGRAPHIC_MODELS,
            pipeline_label="infographic",
        )

    def run_task_i0(self) -> TaskI0Output:
        """Run Task I0: Content Analysis for Infographic."""
        log = _make_step_logger("i0")
        log("Running Task I0: Content Analysis...")
        result = run_task_i0(
            source_essay=self.source_essay,
            client=self.text_client,
            model=self._model_for("i0"),
            max_output_tokens=self._max_tokens_for("i0"),
        )
        self._save_yaml(result.model_dump(), INFOGRAPHIC_OUTPUT_FILES["i0"])
        log(f"  Title: {result.title}")
        log(f"  Key points: {len(result.key_points)}")
        log(
            f"  Structure: {result.content_structure.primary_pattern} ({result.content_structure.section_count} sections)"
        )
        return result

    def run_task_i1(
        self, i0_output: TaskI0Output, style_prompt: str | None = None
    ) -> TaskI1Output:
        """Run Task I1: Design Specification for Infographic."""
        log = _make_step_logger("i1")
        log("Running Task I1: Design Specification...")
        result = run_task_i1(
            source_essay=self.source_essay,
            i0_output=i0_output,
            client=self.text_client,
            model=self._model_for("i1"),
            style_prompt=style_prompt,
            max_output_tokens=self._max_tokens_for("i1"),
        )
        self._save_yaml(result.model_dump(), INFOGRAPHIC_OUTPUT_FILES["i1"])
        log(f"  Layout: {result.layout_type} ({result.orientation})")
        log(f"  Sections: {len(result.sections)}")
        log(f"  Style: {result.visual_style}")
        return result

    def run_task_i2(
        self,
        i0_output: TaskI0Output,
        i1_output: TaskI1Output,
        num_variants: int = 3,
        style_prompt: str | None = None,
        provider: str = "gemini",
        quality: str | None = None,
    ) -> TaskI2Output:
        """Run Task I2: Image Prompt Generation for Infographic."""
        log = _make_step_logger("i2")
        log(f"Running Task I2: Image Prompt Generation ({num_variants} variant(s))...")
        result = run_task_i2(
            source_essay=self.source_essay,
            i0_output=i0_output,
            i1_output=i1_output,
            num_variants=num_variants,
            client=self.text_client,
            model=self._model_for("i2"),
            style_prompt=style_prompt,
            max_output_tokens=self._max_tokens_for("i2"),
            provider=provider,
            quality=quality,
        )
        self._save_yaml(result.model_dump(), INFOGRAPHIC_OUTPUT_FILES["i2"])
        log(f"  Variants generated: {len(result.variants)}")
        for v in result.variants:
            log(f"    v{v.variant_number}: {v.interpretation}")

        self._save_infographic_prompt_files(result)

        return result

    def _save_infographic_prompt_files(self, i2_output: TaskI2Output) -> None:
        """Save one prompt YAML per variant under prompts/."""
        prompts_dir = self.output_dir / "prompts"
        prompts_dir.mkdir(exist_ok=True)
        for v in i2_output.variants:
            prompt_data = {
                "variant_number": v.variant_number,
                "interpretation": v.interpretation,
                "full_prompt": v.full_prompt,
                "generation_notes": v.generation_notes.model_dump(),
            }
            filename = f"infographic-v{v.variant_number}-prompt.yaml"
            self._save_yaml(prompt_data, f"prompts/{filename}")

    def run_task_i2_with_critique(
        self,
        i0_output: TaskI0Output,
        i1_output: TaskI1Output,
        num_variants: int = 3,
        style_prompt: str | None = None,
        provider: str = "gemini",
        quality: str | None = None,
        skip_critique: bool = True,
        critique_rounds: int = 1,
    ) -> TaskI2Output:
        """Run Task I2 with optional critique-refine loop.

        Produces v1, audits it against i0/i1 (entity consistency, semantic
        loss, coverage, flow, text density), then refines. Refinement is
        skipped for a round when the critique finds no critical or important
        issues. When skip_critique is True, behaves identically to
        run_task_i2().

        Args:
            i0_output: Output from Task I0.
            i1_output: Output from Task I1.
            num_variants: Number of prompt variants to generate.
            style_prompt: Optional style transfer prompt.
            provider: Image generation provider.
            quality: Resolved rendering quality tier.
            skip_critique: If True, skip the critique-refine loop.
            critique_rounds: Number of critique-refine iterations.

        Returns:
            TaskI2Output — final refined version, or v1 if critique skipped.
        """
        from .tasks.task_i2_critique import _needs_refinement

        if skip_critique:
            return self.run_task_i2(
                i0_output=i0_output,
                i1_output=i1_output,
                num_variants=num_variants,
                style_prompt=style_prompt,
                provider=provider,
                quality=quality,
            )

        log = _make_step_logger("i2")
        log(f"Running Task I2: Image Prompt Generation ({num_variants} variant(s))...")
        current = run_task_i2(
            source_essay=self.source_essay,
            i0_output=i0_output,
            i1_output=i1_output,
            num_variants=num_variants,
            client=self.text_client,
            model=self._model_for("i2"),
            style_prompt=style_prompt,
            max_output_tokens=self._max_tokens_for("i2"),
            provider=provider,
            quality=quality,
        )
        log(f"  Variants generated: {len(current.variants)}")

        # Save initial version
        step = 1
        self._save_yaml(current.model_dump(), f"task-i2-{step}-prompts.yaml")
        log(f"  Saved → task-i2-{step}-prompts.yaml")

        for round_num in range(1, critique_rounds + 1):
            round_label = (
                f" (round {round_num}/{critique_rounds})" if critique_rounds > 1 else ""
            )

            # Critique
            step += 1
            log(f"Running Task I2 Critique: Prompt Audit{round_label}...")
            critique = run_task_i2_critique(
                i0_output=i0_output,
                i1_output=i1_output,
                i2_output=current,
                client=self.text_client,
                model=self._model_for("i2_critique"),
                style_prompt=style_prompt,
                quality=quality,
                max_output_tokens=self._max_tokens_for("i2_critique"),
            )
            self._save_yaml(critique.model_dump(), f"task-i2-{step}-critique.yaml")
            log(f"  Prompt issues: {len(critique.prompt_issues)}")
            log(f"  Dropped key content: {len(critique.dropped_key_content)}")

            if not _needs_refinement(critique):
                log("  No critical/important issues — skipping refinement")
                break

            # Refine
            step += 1
            log(f"Running Task I2 Refine: Correcting prompts{round_label}...")
            current = run_task_i2_refine(
                i0_output=i0_output,
                i1_output=i1_output,
                i2_output=current,
                critique=critique,
                client=self.text_client,
                model=self._model_for("i2_refine"),
                style_prompt=style_prompt,
                quality=quality,
                provider=provider,
                max_output_tokens=self._max_tokens_for("i2_refine"),
            )
            self._save_yaml(current.model_dump(), f"task-i2-{step}-prompts.yaml")
            log(f"  Saved → task-i2-{step}-prompts.yaml")

        # Save final version as canonical
        self._save_yaml(current.model_dump(), INFOGRAPHIC_OUTPUT_FILES["i2"])
        self._save_infographic_prompt_files(current)

        return current

    def _run_infographic_images(
        self,
        i2_output: TaskI2Output,
        provider: str = "gemini",
        size: str | None = None,
        aspect_ratio: str = "16:9",
        quality: str | None = None,
        image_model: str | None = None,
    ) -> None:
        """Generate images for infographic variants."""
        if not IMAGE_GEN_AVAILABLE:
            print("[images] Image generation not available (missing pixbridge package)")
            return

        from pixbridge.models import (
            GenerationNotes as ImageGenNotes,
            ImagePrompt as ImageGenPrompt,
        )

        def build(variant) -> BuiltPrompt:
            return BuiltPrompt(
                ImageGenPrompt(
                    full_prompt=variant.full_prompt,
                    generation_notes=ImageGenNotes(
                        **variant.generation_notes.model_dump()
                    ),
                )
            )

        batch = ImageBatchGenerator(
            client_factory=lambda: self._make_image_client(provider),
            failure_sink=self.image_failures,
            images_dir=self.output_dir / "images",
            label="variant",
            build_prompt=build,
            settings=BatchSettings(
                size=size,
                aspect_ratio=aspect_ratio,
                quality=quality,
                image_model=image_model,
            ),
        )
        items = [
            BatchItem(
                index=v.variant_number,
                item_id=f"infographic-v{v.variant_number}",
                payload=v,
            )
            for v in i2_output.variants
        ]
        result = batch.run_sequential(items, skip_existing=True)
        batch.report(result)

    def run_infographic_pipeline(self, config: InfographicRunConfig) -> Path:
        """Run the full infographic pipeline.

        Analyzes source content and generates one or more complete
        infographic images via AI image generation.
        """
        image_model = config.image_model or self._image_model_for(config.provider)

        self._set_image_run_defaults(
            ref_images=config.ref_images,
            output_format=config.output_format,
            output_compression=config.output_compression,
        )

        if config.from_step not in INFOGRAPHIC_STEPS:
            raise ValueError(
                f"Invalid from_step: {config.from_step}. Valid steps: {', '.join(INFOGRAPHIC_STEPS)}"
            )
        if config.to_step not in INFOGRAPHIC_STEPS:
            raise ValueError(
                f"Invalid to_step: {config.to_step}. Valid steps: {', '.join(INFOGRAPHIC_STEPS)}"
            )

        start_index = INFOGRAPHIC_STEPS.index(config.from_step)
        end_index = INFOGRAPHIC_STEPS.index(config.to_step)

        if start_index > end_index:
            raise ValueError(
                f"--from {config.from_step} is after --to {config.to_step}. "
                f"Step order: {', '.join(INFOGRAPHIC_STEPS)}"
            )

        print("Running Infographic Pipeline")
        print(f"  Source: {self.source_path}")
        print(f"  Output: {self.output_dir}")
        print(f"  Variants: {config.num_variants}")
        if config.from_step != "i0":
            print(f"  Starting from: {config.from_step}")
        if config.to_step != "images":
            print(f"  Stopping after: {config.to_step}")
        print()

        # Load style prompt if provided
        style_prompt = None
        if config.style_prompt_path:
            style_path = Path(config.style_prompt_path)
            if not style_path.exists():
                raise FileNotFoundError(
                    f"Style prompt file not found: {config.style_prompt_path}"
                )
            style_prompt = style_path.read_text()
            print(f"Loaded style prompt from: {config.style_prompt_path}")

        # Load dependencies if starting from a later step
        if start_index > 0:
            self._load_infographic_dependencies(
                cast(InfographicStepName, config.from_step)
            )
            print("Loaded existing outputs for dependencies")
            print()

        # Initialize outputs
        task_i0_output: TaskI0Output | None = getattr(self, "task_i0_output", None)
        task_i1_output: TaskI1Output | None = getattr(self, "task_i1_output", None)
        task_i2_output: TaskI2Output | None = getattr(self, "task_i2_output", None)

        # Task I0: Content Analysis
        if start_index <= INFOGRAPHIC_STEPS.index("i0") <= end_index:
            task_i0_output = self.run_task_i0()
            print()

        # Task I1: Design Specification
        if start_index <= INFOGRAPHIC_STEPS.index("i1") <= end_index:
            # i0 precedes i1 and is generated or loaded before this point.
            assert task_i0_output is not None
            task_i1_output = self.run_task_i1(
                i0_output=task_i0_output, style_prompt=style_prompt
            )
            print()

        # Task I2: Image Prompt Generation
        if start_index <= INFOGRAPHIC_STEPS.index("i2") <= end_index:
            # i0/i1 precede i2 and are generated or loaded before this point.
            assert task_i0_output is not None
            assert task_i1_output is not None
            task_i2_output = self.run_task_i2_with_critique(
                i0_output=task_i0_output,
                i1_output=task_i1_output,
                num_variants=config.num_variants,
                style_prompt=style_prompt,
                provider=config.provider,
                quality=config.quality,
                skip_critique=config.skip_critique,
                critique_rounds=config.critique_rounds,
            )
            print()
        elif INFOGRAPHIC_STEPS.index(
            "images"
        ) <= end_index and start_index > INFOGRAPHIC_STEPS.index("i2"):
            # Loading I2 output for images-only run
            if not self._load_infographic_task_output("i2"):
                raise FileNotFoundError(
                    f"Cannot run images: missing {self.output_dir / INFOGRAPHIC_OUTPUT_FILES['i2']}"
                )
            task_i2_output = getattr(self, "task_i2_output", None)

        # Images
        if (
            not config.skip_images
            and start_index <= INFOGRAPHIC_STEPS.index("images") <= end_index
        ):
            if task_i2_output:
                self._run_infographic_images(
                    i2_output=task_i2_output,
                    provider=config.provider,
                    size=config.size,
                    aspect_ratio=config.aspect_ratio,
                    quality=config.quality,
                    image_model=image_model,
                )

        self._write_manifest("infographic", config)

        print()
        print("Infographic pipeline complete!")
        print(f"Output directory: {self.output_dir}")

        return self.output_dir
