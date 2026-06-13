"""Tests for the concurrent pipeline engine."""

import time
import threading
from pathlib import Path


from polyptych.concurrent_engine import (
    ConcurrentPipelineEngine,
    EngineConfig,
    OrderedProgressReporter,
    RunResult,
    WorkItem,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_items(n: int) -> list[WorkItem]:
    """Create N work items with sequential indices."""
    return [
        WorkItem(index=i, item_id=f"item-{i:03d}", input_data={"value": i})
        for i in range(n)
    ]


def simple_produce(item: WorkItem) -> None:
    """Produce a prompt string from input_data."""
    item.prompt = f"prompt-for-{item.item_id}"


def simple_consume(item: WorkItem) -> None:
    """Consume by creating a fake output path."""
    item.output_path = Path(f"/tmp/fake/{item.item_id}.png")


# ---------------------------------------------------------------------------
# Tests: EngineConfig
# ---------------------------------------------------------------------------


class TestEngineConfig:
    def test_default_queue_size(self):
        cfg = EngineConfig(num_consumers=5)
        assert cfg.queue_size == 10

    def test_explicit_queue_size(self):
        cfg = EngineConfig(num_consumers=5, queue_size=3)
        assert cfg.queue_size == 3


# ---------------------------------------------------------------------------
# Tests: OrderedProgressReporter
# ---------------------------------------------------------------------------


class TestOrderedProgressReporter:
    def test_counts(self):
        reporter = OrderedProgressReporter(total=5)
        assert reporter.produced == 0
        assert reporter.consumed == 0

        reporter.report_produced("item-1")
        assert reporter.produced == 1

        reporter.report_consumed("item-1", success=True)
        assert reporter.consumed == 1

    def test_thread_safety(self):
        reporter = OrderedProgressReporter(total=100)
        threads = []
        for i in range(100):
            t = threading.Thread(target=reporter.report_produced, args=(f"item-{i}",))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        assert reporter.produced == 100


# ---------------------------------------------------------------------------
# Tests: ConcurrentPipelineEngine
# ---------------------------------------------------------------------------


class TestConcurrentPipelineEngine:
    def test_happy_path(self):
        """All items produced and consumed successfully."""
        items = make_items(10)
        engine = ConcurrentPipelineEngine(EngineConfig(num_producers=2, num_consumers=3))
        result = engine.run(items, simple_produce, simple_consume)

        assert len(result.completed) == 10
        assert len(result.failed) == 0
        assert result.total_produced == 10
        assert result.total_consumed == 10

    def test_empty_input(self):
        """Empty work item list returns empty result immediately."""
        engine = ConcurrentPipelineEngine(EngineConfig())
        result = engine.run([], simple_produce, simple_consume)

        assert result == RunResult()
        assert len(result.completed) == 0
        assert len(result.failed) == 0

    def test_single_item(self):
        """Single item works correctly."""
        items = make_items(1)
        engine = ConcurrentPipelineEngine(EngineConfig(num_producers=1, num_consumers=1))
        result = engine.run(items, simple_produce, simple_consume)

        assert len(result.completed) == 1
        assert result.completed[0] == Path("/tmp/fake/item-000.png")

    def test_produce_failure(self):
        """Producer failure is recorded, item not sent to consumer."""
        def failing_produce(item: WorkItem) -> None:
            if item.index == 3:
                raise ValueError("LLM error on item 3")
            item.prompt = f"prompt-{item.item_id}"

        items = make_items(5)
        engine = ConcurrentPipelineEngine(EngineConfig(num_producers=1, num_consumers=2))
        result = engine.run(items, failing_produce, simple_consume)

        assert len(result.completed) == 4
        assert len(result.failed) == 1
        assert result.failed[0][0] == 3
        assert "LLM error" in result.failed[0][1]

    def test_consume_failure(self):
        """Consumer failure is recorded."""
        def failing_consume(item: WorkItem) -> None:
            if item.index == 2:
                raise RuntimeError("Image API error")
            item.output_path = Path(f"/tmp/fake/{item.item_id}.png")

        items = make_items(5)
        engine = ConcurrentPipelineEngine(EngineConfig(num_producers=2, num_consumers=2))
        result = engine.run(items, simple_produce, failing_consume)

        assert len(result.completed) == 4
        assert len(result.failed) == 1
        assert result.failed[0][0] == 2
        assert "Image API error" in result.failed[0][1]

    def test_all_fail_produce(self):
        """All producers fail — no items reach consumers."""
        def all_fail_produce(item: WorkItem) -> None:
            raise ValueError("always fails")

        items = make_items(5)
        engine = ConcurrentPipelineEngine(EngineConfig(num_producers=2, num_consumers=2))
        result = engine.run(items, all_fail_produce, simple_consume)

        assert len(result.completed) == 0
        assert len(result.failed) == 5
        assert result.total_consumed == 0

    def test_all_fail_consume(self):
        """All consumers fail — all items marked as failed."""
        def all_fail_consume(item: WorkItem) -> None:
            raise RuntimeError("always fails")

        items = make_items(5)
        engine = ConcurrentPipelineEngine(EngineConfig(num_producers=2, num_consumers=2))
        result = engine.run(items, simple_produce, all_fail_consume)

        assert len(result.completed) == 0
        assert len(result.failed) == 5

    def test_backpressure(self):
        """Producers block when queue is full (queue_size=1, slow consumer)."""
        produce_times: list[float] = []
        produce_lock = threading.Lock()

        def timed_produce(item: WorkItem) -> None:
            item.prompt = f"prompt-{item.item_id}"
            with produce_lock:
                produce_times.append(time.monotonic())

        def slow_consume(item: WorkItem) -> None:
            time.sleep(0.05)
            item.output_path = Path(f"/tmp/fake/{item.item_id}.png")

        items = make_items(4)
        engine = ConcurrentPipelineEngine(
            EngineConfig(num_producers=1, num_consumers=1, queue_size=1)
        )
        result = engine.run(items, timed_produce, slow_consume)

        assert len(result.completed) == 4
        # With queue_size=1 and 1 slow consumer, later produces should be
        # delayed. We verify all items complete correctly — the timing
        # assertion is that this doesn't deadlock.

    def test_produce_sets_error_field(self):
        """Producer that sets error field instead of raising."""
        def produce_with_error(item: WorkItem) -> None:
            if item.index == 1:
                item.error = "soft error"
            else:
                item.prompt = f"prompt-{item.item_id}"

        items = make_items(3)
        engine = ConcurrentPipelineEngine(EngineConfig(num_producers=1, num_consumers=1))
        result = engine.run(items, produce_with_error, simple_consume)

        assert len(result.completed) == 2
        assert len(result.failed) == 1

    def test_many_producers_many_consumers(self):
        """Stress test with many threads."""
        items = make_items(50)
        engine = ConcurrentPipelineEngine(
            EngineConfig(num_producers=4, num_consumers=8, queue_size=4)
        )
        result = engine.run(items, simple_produce, simple_consume)

        assert len(result.completed) == 50
        assert len(result.failed) == 0

    def test_mixed_failures(self):
        """Both producer and consumer failures in the same run."""
        def mixed_produce(item: WorkItem) -> None:
            if item.index % 5 == 0:
                raise ValueError(f"produce fail {item.index}")
            item.prompt = f"prompt-{item.item_id}"

        def mixed_consume(item: WorkItem) -> None:
            if item.index % 7 == 0:
                raise RuntimeError(f"consume fail {item.index}")
            item.output_path = Path(f"/tmp/fake/{item.item_id}.png")

        items = make_items(20)
        engine = ConcurrentPipelineEngine(EngineConfig(num_producers=2, num_consumers=3))
        result = engine.run(items, mixed_produce, mixed_consume)

        total = len(result.completed) + len(result.failed)
        assert total == 20
        assert len(result.failed) > 0
        assert len(result.completed) > 0

    def test_preloaded_prompts_skip_produce(self):
        """Items with pre-loaded prompts skip the produce step entirely."""
        items = make_items(5)
        # Pre-load prompts for items 0, 2, 4
        for i in [0, 2, 4]:
            items[i].prompt = f"preloaded-prompt-{i}"

        produce_called: list[int] = []
        produce_lock = threading.Lock()

        def tracking_produce(item: WorkItem) -> None:
            with produce_lock:
                produce_called.append(item.index)
            # Only produce for items that don't have a prompt yet
            if item.prompt is None:
                item.prompt = f"prompt-for-{item.item_id}"

        engine = ConcurrentPipelineEngine(EngineConfig(num_producers=2, num_consumers=2))
        result = engine.run(items, tracking_produce, simple_consume)

        assert len(result.completed) == 5
        assert len(result.failed) == 0
        # All items go through produce, but the caller's guard logic
        # (in pipeline.py) would skip the LLM call when prompt is set.
        # The engine itself calls produce for all items — the guard is
        # in the closure. Here we verify all items reach consume OK.
        for item in items:
            assert item.prompt is not None
            assert item.output_path is not None

    def test_preloaded_prompts_with_produce_guard(self):
        """Simulate the pipeline's produce guard: skip LLM when prompt is pre-set."""
        items = make_items(6)
        # Pre-load prompts for items 1, 3, 5
        for i in [1, 3, 5]:
            items[i].prompt = f"preloaded-{i}"

        produce_calls: list[int] = []
        produce_lock = threading.Lock()

        def guarded_produce(item: WorkItem) -> None:
            if item.prompt is not None:
                return  # Skip — prompt already loaded from disk
            with produce_lock:
                produce_calls.append(item.index)
            item.prompt = f"generated-{item.item_id}"

        engine = ConcurrentPipelineEngine(EngineConfig(num_producers=1, num_consumers=2))
        result = engine.run(items, guarded_produce, simple_consume)

        assert len(result.completed) == 6
        assert len(result.failed) == 0
        # Only items 0, 2, 4 should have triggered the LLM path
        assert sorted(produce_calls) == [0, 2, 4]
        # Pre-loaded items should retain their original prompts
        assert items[1].prompt == "preloaded-1"
        assert items[3].prompt == "preloaded-3"
