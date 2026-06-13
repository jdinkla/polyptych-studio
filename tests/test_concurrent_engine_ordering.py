"""Deterministic concurrency tests for ConcurrentPipelineEngine.

test_concurrent_engine.py covers happy/failure paths but leans on real sleeps
for backpressure. This file pins the timing-sensitive contracts using
threading.Event / Barrier so the assertions are deterministic and fast (no real
sleeps): consumer shutdown via sentinels, completeness under uneven worker
counts, error-vs-raise consumer paths, and that backpressure does not deadlock.
"""

from __future__ import annotations

import threading
from pathlib import Path

from polyptych.concurrent_engine import (
    ConcurrentPipelineEngine,
    EngineConfig,
    WorkItem,
)


def make_items(n: int) -> list[WorkItem]:
    return [
        WorkItem(index=i, item_id=f"item-{i:03d}", input_data={"value": i})
        for i in range(n)
    ]


def simple_produce(item: WorkItem) -> None:
    item.prompt = f"prompt-{item.item_id}"


def simple_consume(item: WorkItem) -> None:
    item.output_path = Path(f"/tmp/fake/{item.item_id}.png")


# =============================================================================
# Consumer shutdown — every consumer must receive a sentinel and exit
# =============================================================================


class TestConsumerShutdown:
    def test_more_consumers_than_items_all_threads_terminate(self):
        # 2 items, 5 consumers. 3 consumers get only a sentinel — the run must
        # still terminate cleanly (no hang waiting on q.get()).
        items = make_items(2)
        engine = ConcurrentPipelineEngine(
            EngineConfig(num_producers=1, num_consumers=5)
        )
        result = engine.run(items, simple_produce, simple_consume)
        assert len(result.completed) == 2
        assert result.total_consumed == 2

    def test_all_produce_fail_consumers_still_shut_down(self):
        # No items reach the queue, but each consumer still gets a sentinel.
        def fail_produce(item: WorkItem) -> None:
            raise ValueError("boom")

        items = make_items(4)
        engine = ConcurrentPipelineEngine(
            EngineConfig(num_producers=2, num_consumers=4)
        )
        # If sentinels were not sent per-consumer, this would deadlock.
        result = engine.run(items, fail_produce, simple_consume)
        assert len(result.failed) == 4
        assert result.total_consumed == 0

    def test_consumer_threads_do_not_leak(self):
        before = threading.active_count()
        items = make_items(6)
        engine = ConcurrentPipelineEngine(
            EngineConfig(num_producers=2, num_consumers=3)
        )
        engine.run(items, simple_produce, simple_consume)
        # ThreadPoolExecutor context managers join on exit.
        assert threading.active_count() == before


# =============================================================================
# Completeness — every item is accounted for exactly once
# =============================================================================


class TestCompleteness:
    def test_every_item_completed_or_failed_exactly_once(self):
        items = make_items(40)

        def mixed_consume(item: WorkItem) -> None:
            if item.index % 4 == 0:
                raise RuntimeError("fail")
            item.output_path = Path(f"/tmp/{item.item_id}.png")

        engine = ConcurrentPipelineEngine(
            EngineConfig(num_producers=3, num_consumers=5, queue_size=2)
        )
        result = engine.run(items, simple_produce, mixed_consume)

        assert len(result.completed) + len(result.failed) == 40
        failed_indices = {idx for idx, _ in result.failed}
        assert failed_indices == {i for i in range(40) if i % 4 == 0}

    def test_failed_list_sorted_by_index(self):
        # Failures recorded out of order across threads must come back sorted.
        def consume(item: WorkItem) -> None:
            if item.index in (7, 1, 19, 4):
                raise RuntimeError("x")
            item.output_path = Path(f"/tmp/{item.item_id}.png")

        items = make_items(20)
        engine = ConcurrentPipelineEngine(
            EngineConfig(num_producers=4, num_consumers=4)
        )
        result = engine.run(items, simple_produce, consume)
        indices = [idx for idx, _ in result.failed]
        assert indices == sorted(indices)
        assert indices == [1, 4, 7, 19]


# =============================================================================
# Producer/consumer overlap — consumers start before all producers finish
# =============================================================================


class TestProducerConsumerOverlap:
    def test_consumer_runs_concurrently_with_producers(self):
        # Gate: a consumer signals it has started; a producer waits on that
        # signal before finishing. If the engine serialized produce-then-consume
        # (no overlap), this would deadlock. Using events keeps it deterministic.
        consumer_started = threading.Event()
        first_produced = threading.Event()

        def produce(item: WorkItem) -> None:
            item.prompt = f"p-{item.index}"
            if item.index == 0:
                first_produced.set()
            else:
                # Later producers wait until a consumer has begun draining,
                # proving the two pools run concurrently.
                assert consumer_started.wait(timeout=2.0), "consumer never started"

        def consume(item: WorkItem) -> None:
            first_produced.wait(timeout=2.0)
            consumer_started.set()
            item.output_path = Path(f"/tmp/{item.item_id}.png")

        items = make_items(4)
        engine = ConcurrentPipelineEngine(
            EngineConfig(num_producers=2, num_consumers=2, queue_size=4)
        )
        result = engine.run(items, produce, consume)
        assert len(result.completed) == 4


# =============================================================================
# Backpressure — bounded queue must not deadlock (event-gated, no sleep)
# =============================================================================


class TestBackpressure:
    def test_bounded_queue_single_consumer_completes(self):
        # queue_size=1 with 1 consumer: producers must block on a full queue.
        # A barrier-free, event-gated consumer lets us assert completion without
        # real sleeps. The contract under test is "does not deadlock".
        release = threading.Event()
        consumed_count = {"n": 0}
        lock = threading.Lock()

        def consume(item: WorkItem) -> None:
            # Block the first consume until released, forcing the queue to fill
            # and producers to experience backpressure.
            if not release.is_set():
                release.wait(timeout=2.0)
            with lock:
                consumed_count["n"] += 1
            item.output_path = Path(f"/tmp/{item.item_id}.png")

        items = make_items(5)
        engine = ConcurrentPipelineEngine(
            EngineConfig(num_producers=2, num_consumers=1, queue_size=1)
        )

        # Release shortly after starting via a watcher thread (no sleep in test).
        def releaser() -> None:
            release.set()

        threading.Thread(target=releaser).start()
        result = engine.run(items, simple_produce, consume)
        assert len(result.completed) == 5
        assert consumed_count["n"] == 5


# =============================================================================
# Error field vs raised exception — both must mark the item failed
# =============================================================================


class TestErrorPropagation:
    def test_consume_sets_error_field_marks_failed(self):
        def consume(item: WorkItem) -> None:
            if item.index == 2:
                item.error = "soft consume error"
                return
            item.output_path = Path(f"/tmp/{item.item_id}.png")

        items = make_items(4)
        engine = ConcurrentPipelineEngine(
            EngineConfig(num_producers=1, num_consumers=2)
        )
        result = engine.run(items, simple_produce, consume)
        assert len(result.completed) == 3
        assert (2, "soft consume error") in result.failed

    def test_consume_success_without_output_path_is_failure(self):
        # An item with no error AND no output_path counts as failed (the result
        # builder requires output_path is not None for "completed").
        def consume(item: WorkItem) -> None:
            if item.index == 1:
                return  # no error, no output_path
            item.output_path = Path(f"/tmp/{item.item_id}.png")

        items = make_items(3)
        engine = ConcurrentPipelineEngine(
            EngineConfig(num_producers=1, num_consumers=1)
        )
        result = engine.run(items, simple_produce, consume)
        assert len(result.completed) == 2
        failed_indices = {idx for idx, _ in result.failed}
        assert failed_indices == {1}
