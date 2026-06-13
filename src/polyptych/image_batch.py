"""Shared image-batch-generation engine used by all pipelines.

Every image-producing pipeline follows the same loop: iterate prompts →
skip existing outputs → build a provider-ready prompt → generate → rename
to a stable item id → catch/log/continue → report counts. This module owns
that loop in its three execution shapes (sequential, interleaved chunks,
producer-consumer concurrent). Pipelines compose an ``ImageBatchGenerator``
parameterized by an item label, a prompt-builder hook, and an ImageClient
factory; everything else (skip/resume logic, error capture, renaming,
thread-local clients, progress reporting) lives here.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .pipeline_config import _make_step_logger

if TYPE_CHECKING:
    from pixbridge.client import ImageClient
    from pixbridge.models import ImagePrompt as ImageGenPrompt

    from .concurrent_engine import RunResult, WorkItem

logger = logging.getLogger(__name__)


@dataclass
class BatchItem:
    """One image to generate.

    ``item_id`` is the stable output basename (e.g. ``slide-02``,
    ``scene-003``, ``infographic-v1``); the generated file is renamed to
    ``{item_id}{suffix}`` and existence checks glob ``{item_id}.*``.
    ``payload`` is the pipeline-specific prompt data fed to the
    ``build_prompt`` hook.
    """

    index: int
    item_id: str
    payload: Any


@dataclass
class BuiltPrompt:
    """Provider-ready prompt plus optional reference images.

    ``ref_paths=None`` routes through ``ImageClient.generate_image``; a list
    (possibly empty) routes through ``generate_image_with_optional_refs`` so
    consistency-lock reference images reach providers that support them.
    """

    prompt: ImageGenPrompt
    ref_paths: list[Path] | None = None


@dataclass
class BatchSettings:
    """Provider-independent generation knobs shared by every pipeline."""

    size: str | None = None
    aspect_ratio: str = "16:9"
    quality: str | None = None
    image_model: str | None = None


@dataclass
class BatchResult:
    """Outcome of a batch run: generated paths, per-item failures, skip count."""

    generated: list[Path] = field(default_factory=list)
    failed: list[tuple[int, str]] = field(default_factory=list)
    skipped: int = 0

    def extend(self, other: BatchResult) -> None:
        self.generated.extend(other.generated)
        self.failed.extend(other.failed)
        self.skipped += other.skipped


@dataclass
class ImageFailure:
    """One image that failed to generate, for the run-level aggregate."""

    label: str
    index: int
    error: str

    def __str__(self) -> str:
        return f"{self.label.capitalize()} {self.index}: {self.error}"


class ImageBatchGenerator:
    """Generates a batch of images from pipeline-supplied prompts.

    Args:
        client_factory: Zero-arg callable returning a fresh ImageClient
            (typically ``lambda: self._make_image_client(provider)``).
            Concurrent mode calls it once per consumer thread.
        images_dir: Directory the images are written into.
        label: Item noun for log lines ("slide", "scene", "frame", ...).
        build_prompt: Hook converting a ``BatchItem.payload`` into a
            ``BuiltPrompt``. All pipeline-specific prompt assembly
            (model conversion, consistency locks, style overrides) lives
            in this hook.
        settings: Size/aspect-ratio/quality/model knobs.
        log: Step logger; defaults to the shared "[images]" logger.
        failure_sink: Optional run-level list that every per-item failure is
            appended to (as :class:`ImageFailure`), across all execution
            modes. Pipelines pass their ``image_failures`` attribute so the
            CLI can report an aggregate and exit non-zero at end of run.
    """

    def __init__(
        self,
        *,
        client_factory: Callable[[], ImageClient],
        images_dir: Path,
        label: str,
        build_prompt: Callable[[Any], BuiltPrompt],
        settings: BatchSettings,
        log: Callable[[str], None] | None = None,
        failure_sink: list[ImageFailure] | None = None,
    ) -> None:
        self.client_factory = client_factory
        self.images_dir = images_dir
        self.label = label
        self.build_prompt = build_prompt
        self.settings = settings
        self.log = log or _make_step_logger("images")
        self.failure_sink = failure_sink
        self._tls = threading.local()
        self.images_dir.mkdir(parents=True, exist_ok=True)

    # ── Single-item core ──

    def image_exists(self, item_id: str) -> bool:
        """True if any output file for this item id already exists."""
        return bool(list(self.images_dir.glob(f"{item_id}.*")))

    def _generate_one(self, client: ImageClient, item: BatchItem) -> Path:
        """Build the prompt, generate the image, and rename it to the item id."""
        from .ref_utils import generate_image_with_optional_refs

        built = self.build_prompt(item.payload)
        s = self.settings
        if built.ref_paths is None:
            image_path = client.generate_image(
                prompt=built.prompt,
                output_dir=self.images_dir,
                model=s.image_model,
                size=s.size,
                aspect_ratio=s.aspect_ratio,
                quality=s.quality,
            )
        else:
            image_path = generate_image_with_optional_refs(
                client,
                built.prompt,
                built.ref_paths,
                self.images_dir,
                model=s.image_model,
                size=s.size,
                aspect_ratio=s.aspect_ratio,
                quality=s.quality,
            )
        new_path = self.images_dir / f"{item.item_id}{image_path.suffix}"
        image_path.rename(new_path)
        return new_path

    # ── Sequential mode ──

    def run_sequential(
        self,
        items: Iterable[BatchItem],
        *,
        skip_existing: bool = False,
        client: ImageClient | None = None,
    ) -> BatchResult:
        """Generate items one at a time, isolating per-item failures.

        Does not emit the summary lines — call :meth:`report` afterwards
        (interleaved mode reuses this per chunk and reports once at the end).
        """
        result = BatchResult()
        if client is None:
            client = self.client_factory()
        for item in items:
            if skip_existing and self.image_exists(item.item_id):
                result.skipped += 1
                continue
            self.log(f"  Generating image for {self.label} {item.index}...")
            try:
                new_path = self._generate_one(client, item)
                result.generated.append(new_path)
                self.log(f"    Saved: {new_path}")
            except Exception as e:  # noqa: BLE001 — per-item isolation by design
                error_msg = f"{type(e).__name__}: {e}"
                result.failed.append((item.index, error_msg))
                self._record_failure(item.index, error_msg)
                self.log(
                    f"    WARNING: Failed to generate image for {self.label} "
                    f"{item.index}: {error_msg}"
                )
                logger.warning(
                    "Failed to generate image for %s %s",
                    self.label,
                    item.index,
                    exc_info=True,
                )
        return result

    def _record_failure(self, index: int, error: str) -> None:
        """Append a per-item failure to the run-level sink, if one is set."""
        if self.failure_sink is not None:
            self.failure_sink.append(ImageFailure(self.label, index, error))

    def report(self, result: BatchResult) -> None:
        """Emit the skip/generated/failed summary for a batch result."""
        if result.skipped:
            self.log(f"  Skipped {result.skipped} existing image(s)")
        self.log(f"  Generated: {len(result.generated)}, Failed: {len(result.failed)}")
        if result.failed:
            self.log(f"WARNING: {len(result.failed)} image(s) failed to generate:")
            for num, err in result.failed:
                self.log(f"  - {self.label.capitalize()} {num}: {err}")

    # ── Interleaved mode ──

    def run_interleaved(
        self,
        items: Iterator[BatchItem],
        *,
        chunk_size: int,
        skip_existing: bool = False,
        select: Callable[[BatchItem], bool] | None = None,
    ) -> tuple[list[Any], BatchResult]:
        """Alternate prompt and image generation in chunks.

        Pulls ``chunk_size`` items from the (typically LLM-backed) iterator,
        generates their images, then pulls the next chunk. Items rejected by
        ``select`` still have their payload collected (so aggregate prompt
        YAMLs stay complete) but produce no image.

        Returns:
            Tuple of (all payloads in iteration order, combined BatchResult).
        """
        client = self.client_factory()
        all_payloads: list[Any] = []
        combined = BatchResult()
        chunk: list[BatchItem] = []
        chunk_num = 0

        def flush() -> None:
            nonlocal chunk_num
            chunk_num += 1
            self.log(
                f"--- Chunk {chunk_num}: {len(chunk)} prompts generated, "
                f"now generating images ---"
            )
            combined.extend(
                self.run_sequential(chunk, skip_existing=skip_existing, client=client)
            )

        for item in items:
            all_payloads.append(item.payload)
            if select is not None and not select(item):
                continue
            chunk.append(item)
            if len(chunk) >= chunk_size:
                flush()
                chunk = []
        if chunk:
            flush()

        return all_payloads, combined

    # ── Concurrent mode (producer-consumer engine) ──

    def build_preloaded_work_items(
        self,
        items: Iterable[BatchItem],
        *,
        force: bool = False,
    ) -> tuple[list[WorkItem], int]:
        """Build engine work items from already-available prompts.

        Items whose image exists are skipped unless ``force``. The payload is
        stored as the work item's prompt, so producers are no-ops.

        Returns:
            Tuple of (work_items, skipped count).
        """
        from .concurrent_engine import WorkItem

        work_items: list[WorkItem] = []
        skipped = 0
        for item in items:
            if not force and self.image_exists(item.item_id):
                skipped += 1
                continue
            work_items.append(
                WorkItem(
                    index=item.index,
                    item_id=item.item_id,
                    input_data=item.payload,
                    prompt=item.payload,  # Pre-loaded, no LLM needed
                )
            )
        return work_items, skipped

    def build_resumable_work_items(
        self,
        specs: Iterable[BatchItem],
        *,
        force: bool,
        load_yaml: Callable[[str], dict | None],
        parse_prompt: Callable[[dict, int], Any],
        prompts_subdir: str = "prompts",
    ) -> tuple[list[WorkItem], int, int, int]:
        """Build engine work items with full resume logic (prompt + image).

        For each spec (payload = producer input data): items with both a
        saved prompt YAML (``{prompts_subdir}/{item_id}-prompt.yaml``) and an
        existing image are skipped; items with only the prompt are preloaded
        via ``parse_prompt(loaded_yaml, index)`` so consumers run without an
        LLM call; the rest are produced from scratch. ``force`` regenerates
        everything.

        Returns:
            Tuple of (work_items, skipped, preloaded, from_scratch).
        """
        from .concurrent_engine import WorkItem

        work_items: list[WorkItem] = []
        skipped = 0
        preloaded = 0
        from_scratch = 0
        for spec in specs:
            prompt_rel = f"{prompts_subdir}/{spec.item_id}-prompt.yaml"
            prompt_exists = (self.images_dir.parent / prompt_rel).exists()
            image_exists = self.image_exists(spec.item_id)

            if not force and prompt_exists and image_exists:
                skipped += 1
                continue

            item = WorkItem(
                index=spec.index,
                item_id=spec.item_id,
                input_data=spec.payload,
            )

            if not force and prompt_exists:
                loaded = load_yaml(prompt_rel)
                if loaded is not None:
                    item.prompt = parse_prompt(loaded, spec.index)
                    preloaded += 1
                else:
                    from_scratch += 1
            else:
                from_scratch += 1

            work_items.append(item)

        return work_items, skipped, preloaded, from_scratch

    def log_resume(
        self,
        work_items: list[WorkItem],
        skipped: int,
        preloaded: int | None = None,
        from_scratch: int | None = None,
    ) -> bool:
        """Emit resume/processing lines; False means nothing is left to do."""
        if preloaded is None:
            total = skipped + len(work_items)
            if skipped > 0:
                self.log(
                    f"  Resume: {skipped} already complete, {len(work_items)} remaining"
                )
        else:
            total = skipped + preloaded + (from_scratch or 0)
            if skipped > 0 or preloaded > 0:
                self.log(
                    f"  Resume: {skipped} already complete, {preloaded} prompts "
                    f"loaded (image-only), {from_scratch} from scratch"
                )

        if not work_items:
            self.log(
                f"All {total} {self.label}s already complete. "
                f"Use --force to regenerate."
            )
            return False

        self.log(f"  Processing {len(work_items)} of {total} {self.label}s...")
        return True

    def _thread_client(self) -> ImageClient:
        """Per-thread ImageClient for consumer threads."""
        if not hasattr(self._tls, "client"):
            self._tls.client = self.client_factory()
        return self._tls.client

    def run_concurrent(
        self,
        work_items: list[WorkItem],
        *,
        num_consumers: int,
        num_producers: int = 1,
        produce_fn: Callable[[WorkItem], None] | None = None,
    ) -> RunResult:
        """Run the producer-consumer engine over the work items.

        Consumers generate images from ``item.prompt`` payloads via the
        ``build_prompt`` hook with one ImageClient per thread. ``produce_fn``
        (pipeline-specific LLM prompt generation) defaults to a no-op for
        images-only runs where prompts are pre-loaded.
        """
        from .concurrent_engine import ConcurrentPipelineEngine, EngineConfig

        def _noop_produce(item: WorkItem) -> None:
            pass

        def consume(item: WorkItem) -> None:
            client = self._thread_client()
            batch_item = BatchItem(
                index=item.index, item_id=item.item_id, payload=item.prompt
            )
            item.output_path = self._generate_one(client, batch_item)

        engine = ConcurrentPipelineEngine(
            EngineConfig(
                num_producers=num_producers,
                num_consumers=num_consumers,
            )
        )
        result = engine.run(work_items, produce_fn or _noop_produce, consume)

        self.log(f"  Completed: {len(result.completed)} images")
        if result.failed:
            self.log(f"  Failed: {len(result.failed)} items:")
            for idx, err in result.failed:
                self._record_failure(idx, err)
                self.log(f"    - {self.label.capitalize()} {idx}: {err}")
        return result
