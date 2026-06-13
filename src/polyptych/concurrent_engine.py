"""Producer-consumer engine for concurrent prompt generation and image generation."""

import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class WorkItem:
    """A single unit of work flowing through the pipeline."""

    index: int
    item_id: str
    input_data: Any
    prompt: Any = None
    output_path: Path | None = None
    error: str | None = None


@dataclass
class EngineConfig:
    """Configuration for the concurrent pipeline engine."""

    num_producers: int = 1
    num_consumers: int = 4
    queue_size: int | None = None  # Default: 2 * num_consumers
    max_retries: int = 0

    def __post_init__(self) -> None:
        if self.queue_size is None:
            self.queue_size = 2 * self.num_consumers


@dataclass
class RunResult:
    """Result summary from a concurrent pipeline run."""

    completed: list[Path] = field(default_factory=list)
    failed: list[tuple[int, str]] = field(default_factory=list)
    total_produced: int = 0
    total_consumed: int = 0


# Sentinel value to signal consumers to shut down
_SENTINEL = object()


class OrderedProgressReporter:
    """Thread-safe progress reporting with counters."""

    def __init__(self, total: int, label: str = "item") -> None:
        self._lock = threading.Lock()
        self._produced = 0
        self._consumed = 0
        self._total = total
        self._label = label

    def report_produced(self, item_id: str) -> None:
        with self._lock:
            self._produced += 1
            print(
                f"[prompt {self._produced}/{self._total}] Generated prompt for {self._label} {item_id}"
            )

    def report_consumed(self, item_id: str, success: bool) -> None:
        with self._lock:
            self._consumed += 1
            status = "OK" if success else "FAILED"
            print(
                f"[image {self._consumed}/{self._total}] {self._label} {item_id}: {status}"
            )

    @property
    def produced(self) -> int:
        with self._lock:
            return self._produced

    @property
    def consumed(self) -> int:
        with self._lock:
            return self._consumed


class ConcurrentPipelineEngine:
    """Generic producer-consumer engine for prompt generation + image generation.

    Producers call produce_fn(work_item) to populate work_item.prompt.
    Consumers call consume_fn(work_item) to populate work_item.output_path.

    The two pools are connected by a bounded queue, providing natural
    backpressure when consumers are slower than producers.
    """

    def __init__(self, config: EngineConfig) -> None:
        self.config = config

    def run(
        self,
        work_items: list[WorkItem],
        produce_fn: Callable[[WorkItem], None],
        consume_fn: Callable[[WorkItem], None],
    ) -> RunResult:
        """Execute the producer-consumer pipeline.

        Args:
            work_items: List of WorkItem objects to process.
            produce_fn: Called per item in producer threads. Should populate
                work_item.prompt (and may save prompt YAML). On failure, should
                set work_item.error.
            consume_fn: Called per item in consumer threads. Should populate
                work_item.output_path. On failure, should set work_item.error.

        Returns:
            RunResult summarising completed and failed items.
        """
        if not work_items:
            return RunResult()

        result = RunResult()
        # queue_size is resolved to a concrete int in ConcurrencyConfig.__post_init__.
        assert self.config.queue_size is not None
        q: queue.Queue = queue.Queue(maxsize=self.config.queue_size)
        progress = OrderedProgressReporter(len(work_items))
        produce_errors: list[tuple[int, str]] = []
        produce_lock = threading.Lock()

        def _produce(item: WorkItem) -> None:
            try:
                produce_fn(item)
                if item.error:
                    with produce_lock:
                        produce_errors.append((item.index, item.error))
                    progress.report_produced(item.item_id)
                    return
                progress.report_produced(item.item_id)
                q.put(item)  # blocks if queue is full (backpressure)
            except Exception as exc:
                item.error = str(exc)
                with produce_lock:
                    produce_errors.append((item.index, str(exc)))
                progress.report_produced(item.item_id)

        def _consume() -> list[WorkItem]:
            """Consumer loop — pulls items until sentinel."""
            finished: list[WorkItem] = []
            while True:
                item = q.get()
                if item is _SENTINEL:
                    q.task_done()
                    break
                try:
                    consume_fn(item)
                    if item.error is None:
                        progress.report_consumed(item.item_id, success=True)
                    else:
                        progress.report_consumed(item.item_id, success=False)
                except Exception as exc:
                    item.error = str(exc)
                    progress.report_consumed(item.item_id, success=False)
                finished.append(item)
                q.task_done()
            return finished

        # Launch pools
        with (
            ThreadPoolExecutor(
                max_workers=self.config.num_producers, thread_name_prefix="producer"
            ) as prod_pool,
            ThreadPoolExecutor(
                max_workers=self.config.num_consumers, thread_name_prefix="consumer"
            ) as cons_pool,
        ):
            # Start consumers — they block on q.get() waiting for work
            consumer_futures = [
                cons_pool.submit(_consume) for _ in range(self.config.num_consumers)
            ]

            # Submit all produce tasks (pool schedules across M threads)
            producer_futures = [prod_pool.submit(_produce, item) for item in work_items]

            # Wait for all producers to finish
            for f in producer_futures:
                f.result()

            # Send one sentinel per consumer to signal shutdown
            for _ in range(self.config.num_consumers):
                q.put(_SENTINEL)

            # Collect consumer results
            all_consumed: list[WorkItem] = []
            for f in consumer_futures:
                all_consumed.extend(f.result())

        # Build result
        result.total_produced = progress.produced
        result.total_consumed = progress.consumed

        for item in all_consumed:
            if item.error is None and item.output_path is not None:
                result.completed.append(item.output_path)
            else:
                result.failed.append((item.index, item.error or "unknown error"))

        # Add produce-phase failures
        for idx, err in produce_errors:
            result.failed.append((idx, f"prompt generation failed: {err}"))

        # Sort failed by index for deterministic output
        result.failed.sort(key=lambda x: x[0])

        return result
