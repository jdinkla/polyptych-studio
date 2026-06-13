"""Base class for SlidePipeline.

Holds initialization and the cross-pipeline plumbing — model resolution,
ImageClient construction, YAML I/O, manifest writing. Each pipeline-type
mixin (task / infographic) inherits from this base.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel

from .client import TextClient
from .image_batch import ImageFailure
from .model_config import (
    ImageModelConfig,
    ModelConfig,
    resolve_image_model,
    resolve_max_output_tokens,
    resolve_model,
    resolve_thinking_budget,
)
from .models import (
    Task1Output,
    Task2Output,
    Task3Output,
    Task4Output,
    Task5Output,
    Task6Output,
    Task7Output,
)
from .run_config import PipelineRunConfig

# Image generation client is optional. Importing here so subclasses can
# call _make_image_client() without re-running the try/except themselves.
# Type-checkers always see ImageClient as imported (via the TYPE_CHECKING
# branch); runtime keeps the optional-dependency behavior via try/except.
if TYPE_CHECKING:
    from pixbridge.client import ImageClient

    IMAGE_GEN_AVAILABLE = True
else:
    try:
        from pixbridge.client import ImageClient

        IMAGE_GEN_AVAILABLE = True
    except ImportError:
        IMAGE_GEN_AVAILABLE = False


class SlidePipelineBase:
    """Shared state and plumbing for every pipeline-type mixin.

    Mixins do not define ``__init__``; they rely on the attributes set up
    here.
    """

    def __init__(
        self,
        source_path: Path | str,
        output_dir: Path | str,
        model_config: ModelConfig | None = None,
        image_model_config: ImageModelConfig | None = None,
        api_key: str | None = None,
        text_provider: str = "gemini",
        text_fallback: list[str] | None = None,
    ):
        """Initialize the pipeline.

        Args:
            source_path: Path to the source essay markdown file.
            output_dir: Directory for output files.
            model_config: Per-task model configuration. If None, loads defaults.
            image_model_config: Per-provider image model configuration. If None, loads defaults.
            api_key: API key for the primary text provider (optional, uses env vars if not provided).
            text_provider: Primary text generation provider (gemini, openai, xai).
            text_fallback: Fallback provider chain. None = auto. ["none"] = disable.
        """
        from .model_config import load_model_config, load_image_model_config

        self.source_path = Path(source_path)
        self.output_dir = Path(output_dir)
        self.model_config = model_config or load_model_config()
        self.image_model_config = image_model_config or load_image_model_config()

        # Initialize clients
        self.text_client = TextClient(
            provider=text_provider,
            fallback=text_fallback,
            api_key=api_key,
            usage_log=self.output_dir / "usage.jsonl",
            model_resolver=lambda task, prov: resolve_model(
                self.model_config, task, prov
            ),
            thinking_budget_resolver=lambda task, prov: resolve_thinking_budget(
                self.model_config, task, prov
            ),
        )

        # Load source essay
        self.source_essay = self.source_path.read_text()

        # Task outputs (populated as tasks run)
        self.task1_output: Task1Output | None = None
        self.task2_output: Task2Output | None = None
        self.task3_output: Task3Output | None = None
        self.task4_output: Task4Output | None = None
        self.task5_output: Task5Output | None = None
        self.task6_output: Task6Output | None = None
        self.task7_output: Task7Output | None = None

        # Per-run image generation defaults populated by run_*_pipeline() from
        # CLI flags (--ref-image, --output-format, --compression). Consumed by
        # _make_image_client() so every ImageClient construction gets them.
        self._image_ref_paths: list[Path] = []
        self._image_output_format: str | None = None
        self._image_output_compression: int | None = None

        # Run-level aggregate of per-item image failures. The batch engine
        # (and blog's bespoke loop) append here via failure_sink; the CLI
        # checks it after the run to report a summary and exit non-zero.
        self.image_failures: list[ImageFailure] = []

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "prompts").mkdir(exist_ok=True)
        (self.output_dir / "images").mkdir(exist_ok=True)

        # Copy source material into output directory
        shutil.copy2(self.source_path, self.output_dir / "source.md")

    def _model_for(self, task_name: str) -> str:
        """Resolve the concrete model string for a pipeline step."""
        return resolve_model(
            self.model_config, task_name, self.text_client.provider_name
        )

    def _max_tokens_for(self, task_name: str) -> int | None:
        """Resolve the max output token limit for a pipeline step."""
        return resolve_max_output_tokens(self.model_config, task_name)

    def _image_model_for(self, provider: str) -> str | None:
        """Resolve the image model string for a provider from config."""
        return resolve_image_model(self.image_model_config, provider)

    def _set_image_run_defaults(
        self,
        *,
        ref_images: list[str] | list[Path] | None = None,
        output_format: str | None = None,
        output_compression: int | None = None,
    ) -> None:
        """Stash per-run image-generation defaults for downstream ImageClients.

        Called from each ``run_*_pipeline`` entry point with values resolved
        from CLI flags. Subsequent ``_make_image_client(...)`` calls fold them
        into every ``ImageClient`` so that --ref-image / --output-format /
        --compression apply uniformly across slides without threading new
        params through every internal method.
        """
        if ref_images:
            self._image_ref_paths = [Path(p) for p in ref_images]
        else:
            self._image_ref_paths = []
        self._image_output_format = output_format
        self._image_output_compression = output_compression

    def _make_image_client(self, provider: str) -> ImageClient:
        """Construct an ImageClient with the current per-run defaults applied.

        All ``ImageClient`` instances throughout the pipeline (main image
        generation, ref-sheet generation, capability probes) share the same
        defaults — the underlying client only consumes them when ``generate_image``
        is actually invoked, so probes and ref-sheet runs are unaffected by the
        ref defaults (those code paths construct their own per-call references).
        """
        return ImageClient(
            provider=provider,
            usage_log=self.output_dir / "usage.jsonl",
            default_output_format=self._image_output_format,
            default_output_compression=self._image_output_compression,
            default_reference_images=self._image_ref_paths or None,
        )

    def _save_yaml(self, data: dict, filename: str) -> Path:
        """Save data to a YAML file atomically.

        Writes to a temp file in the target directory, then os.replace()s it
        into place, so a crash mid-write can never leave a half-written file
        for the resume logic to choke on.
        """
        output_path = self.output_dir / filename
        fd, tmp_path = tempfile.mkstemp(
            dir=output_path.parent, prefix=f".{output_path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w") as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            os.replace(tmp_path, output_path)
        except BaseException:
            with suppress(OSError):
                os.unlink(tmp_path)
            raise
        return output_path

    def _load_yaml(self, filename: str) -> dict | None:
        """Load data from a YAML file if it exists."""
        input_path = self.output_dir / filename
        if input_path.exists():
            with open(input_path) as f:
                return yaml.safe_load(f)
        return None

    def _load_task_output_generic(
        self,
        task_name: str,
        *,
        output_files: Mapping[str, str],
        models: Mapping[str, type[BaseModel]],
        attr_prefix: str = "task_",
    ) -> bool:
        """Load and validate a single task's YAML output into an instance attribute.

        Looks the task's output filename and Pydantic model up in the
        per-pipeline derived maps (themselves built from the ``TaskSpec``
        registry), validates the YAML, and stores the result on
        ``self.{attr_prefix}{task_name}_output``.

        Returns False when the task is untracked (no entry in ``output_files``,
        e.g. an image-only boundary step) or its YAML file is missing. The
        per-pipeline ``_load_<pipeline>_task_output`` methods are thin wrappers
        around this with their own maps and attribute-prefix bound.
        """
        if task_name not in output_files:
            return False

        data = self._load_yaml(output_files[task_name])
        if data is None:
            return False

        output = models[task_name].model_validate(data)
        setattr(self, f"{attr_prefix}{task_name}_output", output)
        return True

    def _load_dependencies_generic(
        self,
        step: str,
        *,
        step_deps: Mapping[str, Sequence[str]],
        output_files: Mapping[str, str],
        models: Mapping[str, type[BaseModel]],
        pipeline_label: str,
        attr_prefix: str = "task_",
    ) -> None:
        """Load every tracked dependency of ``step`` into instance attributes.

        Dependencies that are untracked boundary steps (no entry in
        ``output_files`` — e.g. blog's image-only ``b3``) are skipped because
        there is no YAML to load. Raises ``FileNotFoundError`` listing every
        missing tracked dependency and the files that were expected.

        The per-pipeline ``_load_<pipeline>_dependencies`` methods are thin
        wrappers around this with their step-dependency graph and maps bound.
        """
        missing: list[str] = []
        for dep in step_deps[step]:
            if dep not in output_files:
                # Untracked boundary dependency (image-only step) — nothing to load.
                continue
            if not self._load_task_output_generic(
                dep,
                output_files=output_files,
                models=models,
                attr_prefix=attr_prefix,
            ):
                missing.append(dep)

        if missing:
            missing_files = [f"{self.output_dir / output_files[d]}" for d in missing]
            raise FileNotFoundError(
                f"Cannot run {pipeline_label} step '{step}': "
                f"missing required outputs: {', '.join(missing)}\n"
                f"Expected files:\n  " + "\n  ".join(missing_files)
            )

    @staticmethod
    def _git_commit_id() -> str | None:
        """Return the current short git commit hash, or None if unavailable."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None

    def _write_manifest(
        self,
        pipeline_type: str,
        config: PipelineRunConfig,
    ) -> Path:
        """Write manifest.yaml capturing how this output was generated."""
        # Collect distinct models actually configured for this run
        models_used = sorted(
            set(resolve_model(self.model_config, t) for t in self.model_config.tasks)
        )
        manifest: dict = {
            "pipeline": pipeline_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": self._git_commit_id(),
            "source": self.source_path.name,
            "models": models_used if len(models_used) > 1 else models_used[0],
            "image_provider": config.provider,
            "image_size": config.size,
            "aspect_ratio": config.aspect_ratio,
            "image_quality": config.quality,
            "style_prompt": config.style_prompt_path,
        }
        manifest.update(config._manifest_extras())
        # Strip None values for cleaner output
        manifest = {k: v for k, v in manifest.items() if v is not None}
        return self._save_yaml(manifest, "manifest.yaml")


# Alias used by pipeline mixins so type-checkers can resolve `self.<attr>`
# accesses to the attributes/methods defined on SlidePipelineBase. At runtime
# this is `object`, leaving the SlidePipeline MRO unchanged (the real
# SlidePipelineBase is mixed in via SlidePipeline's bases).
if TYPE_CHECKING:
    PipelineMixin = SlidePipelineBase
else:
    PipelineMixin = object
