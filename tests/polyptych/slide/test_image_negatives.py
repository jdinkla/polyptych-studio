"""Negative prompts reach the image provider even for locally authored YAML."""

from .factories import make_image_prompt
from polyptych.models import SlideImagePrompt


def test_slide_image_build_folds_negatives(slide_pipeline):
    # Local task7 YAML skips finalize_draft, so negatives arrive unfolded.
    image_prompt = make_image_prompt(1)
    image_prompt.generation_notes.negative_prompts = ["blurry text", "logos"]
    batch = slide_pipeline._slide_image_batch("openai", None, "16:9", None, None)

    built = batch.build_prompt(SlideImagePrompt(slide_number=1, image_prompt=image_prompt))

    assert built.prompt.full_prompt.endswith("AVOID: blurry text, logos.")


def test_slide_image_build_is_idempotent(slide_pipeline):
    image_prompt = make_image_prompt(1)
    image_prompt.generation_notes.negative_prompts = ["logos"]
    image_prompt.full_prompt += "\n\nAVOID: logos."
    batch = slide_pipeline._slide_image_batch("openai", None, "16:9", None, None)

    built = batch.build_prompt(SlideImagePrompt(slide_number=1, image_prompt=image_prompt))

    assert built.prompt.full_prompt.count("AVOID: logos.") == 1
