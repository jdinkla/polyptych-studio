"""Shared reference-image utilities.

Currently this is limited to locating a style preset's companion exemplar
image, used by the CLI to seed the reference-image list for providers that
support it (OpenAI gpt-image-2, Gemini).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pixbridge.client import ImageClient
    from pixbridge.models import ImagePrompt as ImageGenPrompt


_STYLE_EXEMPLAR_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def find_style_exemplar(style_path: Path | str | None) -> Path | None:
    """Return a sibling exemplar image for a style-preset .md file, if present.

    Convention: a style preset at ``prompts/style-transfer/<cat>/<name>.md`` may
    have a companion exemplar image at ``prompts/style-transfer/<cat>/<name>.{png,jpg,jpeg,webp}``.
    When generating with a provider that supports reference images (gpt-image-2,
    gemini), the exemplar is passed as the first reference to anchor visual
    style. Returns ``None`` if no companion image exists.
    """
    if style_path is None:
        return None
    p = Path(style_path)
    if not p.is_file():
        return None
    for ext in _STYLE_EXEMPLAR_EXTENSIONS:
        candidate = p.with_suffix(ext)
        if candidate.is_file():
            return candidate
    return None


def generate_image_with_optional_refs(
    image_client: "ImageClient",
    prompt: "ImageGenPrompt",
    frame_ref_paths: list[Path],
    output_dir: Path,
    model: str | None = None,
    size: str | None = None,
    aspect_ratio: str = "16:9",
    quality: str | None = None,
) -> Path:
    """Generate an image, using reference images if any are provided.

    Args:
        image_client: Initialized ImageClient.
        prompt: Image generation prompt.
        frame_ref_paths: Reference image paths (empty = no refs).
        output_dir: Directory to write the generated image.
        model: Image generation model name.
        size: Size preset.
        aspect_ratio: Aspect ratio.
        quality: Quality level.

    Returns:
        Path to the generated image.
    """
    if frame_ref_paths:
        return image_client.generate_image_with_references(
            prompt=prompt,
            reference_images=frame_ref_paths,
            output_dir=output_dir,
            model=model,
            size=size,
            aspect_ratio=aspect_ratio,
            quality=quality,
        )
    return image_client.generate_image(
        prompt=prompt,
        output_dir=output_dir,
        model=model,
        size=size,
        aspect_ratio=aspect_ratio,
        quality=quality,
    )
