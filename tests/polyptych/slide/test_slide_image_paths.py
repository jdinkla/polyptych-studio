"""Tests for the slide pipeline image-generation paths.

test_slide_pipeline_flow.py covers the text tasks (task1-task7) and step-range
control. This file pins the image side that the flow tests stop short of:

- run_images: success, per-slide failure isolation, slide filtering, rename
- the run_from dispatch into interleaved / concurrent / images-only-concurrent
- resume/skip logic in the concurrent paths (existing prompt+image → skipped)

All image generation is mocked via MockImageClient (writes 1x1 PNGs). No real
provider is touched.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from polyptych.pipeline import SlidePipeline, TASK_OUTPUT_FILES
from polyptych.run_config import SlideRunConfig

from ..mock_client import MockImageClient, MockTextClient
from .factories import (
    make_task1_output,
    make_task5_output,
    make_task6_output,
    make_task7_output,
)


def _load_task7(pipeline: SlidePipeline, slide_count: int = 3) -> None:
    """Populate the in-memory task7_output so run_images can run."""
    pipeline.task7_output = make_task7_output(slide_count=slide_count)


def _mock_images(pipeline: SlidePipeline, client: MockImageClient | None = None):
    """Patch _make_image_client to return a MockImageClient."""
    client = client or MockImageClient()
    return patch.object(pipeline, "_make_image_client", return_value=client)


# =============================================================================
# run_images
# =============================================================================


class TestRunImages:
    def test_generates_one_image_per_prompt_and_renames(
        self, slide_pipeline: SlidePipeline
    ):
        _load_task7(slide_pipeline, slide_count=3)
        with _mock_images(slide_pipeline):
            paths = slide_pipeline.run_images(provider="gemini")

        assert len(paths) == 3
        # Files renamed to slide-NN.<ext>
        names = sorted(p.name for p in paths)
        assert names == ["slide-01.png", "slide-02.png", "slide-03.png"]
        for p in paths:
            assert p.exists()

    def test_slides_filter_limits_generation(self, slide_pipeline: SlidePipeline):
        _load_task7(slide_pipeline, slide_count=4)
        with _mock_images(slide_pipeline):
            paths = slide_pipeline.run_images(provider="gemini", slides=[2, 4])

        assert sorted(p.name for p in paths) == ["slide-02.png", "slide-04.png"]

    def test_per_slide_failure_isolated_others_succeed(
        self, slide_pipeline: SlidePipeline
    ):
        _load_task7(slide_pipeline, slide_count=3)

        class FlakyClient(MockImageClient):
            def generate_image(self, prompt, output_dir, **kwargs):
                # Fail on the second call only.
                if self._call_count == 1:
                    self._call_count += 1
                    raise RuntimeError("provider 500")
                return super().generate_image(prompt, output_dir, **kwargs)

        with _mock_images(slide_pipeline, FlakyClient()):
            paths = slide_pipeline.run_images(provider="gemini")

        # One failed → two succeeded, run does not raise.
        assert len(paths) == 2

    def test_raises_without_task7_output(self, slide_pipeline: SlidePipeline):
        slide_pipeline.task7_output = None
        with _mock_images(slide_pipeline), pytest.raises(ValueError, match="Task 7"):
            slide_pipeline.run_images(provider="gemini")


# =============================================================================
# run_from dispatch: plain images step
# =============================================================================


def _seed_text_outputs(pipeline: SlidePipeline) -> None:
    """Write task1/task5/task6/task7 YAMLs (deps for the image steps)."""
    import yaml

    for name, model in [
        ("task1", make_task1_output()),
        ("task5", make_task5_output()),
        ("task6", make_task6_output(slide_count=3)),
        ("task7", make_task7_output(slide_count=3)),
    ]:
        path = pipeline.output_dir / TASK_OUTPUT_FILES[name]
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(model.model_dump(), f)


class TestRunFromImagesStep:
    def test_images_only_step_generates_all(self, slide_pipeline: SlidePipeline):
        _seed_text_outputs(slide_pipeline)
        with _mock_images(slide_pipeline):
            slide_pipeline.run_from(
                SlideRunConfig(from_step="images", to_step="images")
            )

        images = sorted((slide_pipeline.output_dir / "images").glob("slide-*.png"))
        assert len(images) == 3


# =============================================================================
# Interleaved path
# =============================================================================


class TestInterleaved:
    def test_interleave_generates_prompts_and_images(
        self, slide_pipeline: SlidePipeline, mock_client: MockTextClient
    ):
        # task7 prompts come from per-slide LLM calls (batch_size=1 implied).
        _seed_text_outputs(slide_pipeline)
        # interleave uses run_task_07_single_slide, which requests an ImagePrompt
        # schema per slide and wraps it into a SlideImagePrompt.
        from .factories import make_image_prompt

        for i in range(1, 4):
            mock_client.register_structured("task7", make_image_prompt(i))

        with _mock_images(slide_pipeline):
            slide_pipeline.run_from(
                SlideRunConfig(from_step="task7", to_step="images", interleave=2)
            )

        # All three images generated across chunks (2 + 1).
        images = sorted((slide_pipeline.output_dir / "images").glob("slide-*.png"))
        assert len(images) == 3
        # Aggregate task7 YAML written.
        assert (slide_pipeline.output_dir / TASK_OUTPUT_FILES["task7"]).exists()


# =============================================================================
# Concurrent paths
# =============================================================================


class TestConcurrentFull:
    def test_concurrent_full_task7_plus_images(
        self, slide_pipeline: SlidePipeline, mock_client: MockTextClient
    ):
        _seed_text_outputs(slide_pipeline)
        from .factories import make_image_prompt

        # Per-slide task7 calls (concurrent uses run_task_07_single_slide, which
        # requests an ImagePrompt and wraps it). repeat=True because producer
        # threads consume responses in nondeterministic order.
        mock_client.register_structured("task7", make_image_prompt(1), repeat=True)

        with _mock_images(slide_pipeline):
            slide_pipeline.run_from(
                SlideRunConfig(
                    from_step="task7", to_step="images", concurrent=2, force=True
                )
            )

        images = sorted((slide_pipeline.output_dir / "images").glob("slide-*.png"))
        assert len(images) == 3
        # Per-slide prompt YAMLs written by producers.
        prompts = sorted(
            (slide_pipeline.output_dir / "prompts").glob("slide-*-prompt.yaml")
        )
        assert len(prompts) == 3


class TestConcurrentImagesOnly:
    def test_images_only_concurrent_consumes_preloaded_prompts(
        self, slide_pipeline: SlidePipeline
    ):
        _seed_text_outputs(slide_pipeline)
        with _mock_images(slide_pipeline):
            slide_pipeline.run_from(
                SlideRunConfig(from_step="images", to_step="images", concurrent=3)
            )

        images = sorted((slide_pipeline.output_dir / "images").glob("slide-*.png"))
        assert len(images) == 3

    def test_resume_skips_slides_with_existing_image(
        self, slide_pipeline: SlidePipeline
    ):
        _seed_text_outputs(slide_pipeline)
        images_dir = slide_pipeline.output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        # Pre-create slide-01 image — should be skipped (no --force).
        (images_dir / "slide-01.png").write_bytes(b"existing")

        client = MockImageClient()
        with _mock_images(slide_pipeline, client):
            slide_pipeline.run_from(
                SlideRunConfig(from_step="images", to_step="images", concurrent=2)
            )

        # Only 2 of 3 slides generated (slide-01 skipped).
        assert client._call_count == 2

    def test_force_regenerates_existing(self, slide_pipeline: SlidePipeline):
        _seed_text_outputs(slide_pipeline)
        images_dir = slide_pipeline.output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "slide-01.png").write_bytes(b"existing")

        client = MockImageClient()
        with _mock_images(slide_pipeline, client):
            slide_pipeline.run_from(
                SlideRunConfig(
                    from_step="images",
                    to_step="images",
                    concurrent=2,
                    force=True,
                )
            )

        # All 3 regenerated despite existing slide-01.
        assert client._call_count == 3
