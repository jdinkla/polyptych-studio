"""Generic batch orchestration: overlap splitting + parallel execution.

Shared by task_a1_sentence_beats (paragraphs) and task_a2_shot_planning (beats).
Each domain keeps its own spec dataclass (with domain-specific derived fields)
and wraps `split_with_overlap()` to enrich the generic `OverlapBatch` records.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class OverlapBatch(Generic[T]):
    """Generic overlap-split batch carrying core items + before/after context.

    core_start is the 0-based index of the first core item in the original list.
    Callers can derive 1-based IDs or other projections from core_start and
    the lengths of core / context_before / context_after.
    """

    batch_index: int
    core: list[T]
    context_before: list[T]
    context_after: list[T]
    core_start: int


def split_with_overlap(
    items: list[T],
    batch_size: int,
    overlap: int = 0,
) -> list[OverlapBatch[T]]:
    """Split `items` into batches of `batch_size` with `overlap` before/after context.

    The last batch may be shorter than batch_size. Context lists are clamped
    to the available items at either end. Returns [] for empty input.
    """
    batches: list[OverlapBatch[T]] = []
    for idx, start in enumerate(range(0, len(items), batch_size)):
        end = min(start + batch_size, len(items))
        before_start = max(0, start - overlap)
        after_end = min(len(items), end + overlap)
        batches.append(
            OverlapBatch(
                batch_index=idx,
                core=items[start:end],
                context_before=items[before_start:start],
                context_after=items[end:after_end],
                core_start=start,
            )
        )
    return batches


def run_batches(
    specs: list[T],
    process: Callable[[T], R],
    max_workers: int,
) -> list[R]:
    """Run `process(spec)` for each spec, return results in submission order.

    Single-batch fast path: if there is exactly one spec, it runs directly
    without spawning a ThreadPoolExecutor. Otherwise results are collected
    via `as_completed` and re-ordered by the spec's original index so that
    ordering is deterministic regardless of completion order.
    """
    if len(specs) == 1:
        return [process(specs[0])]

    effective_workers = min(len(specs), max_workers)
    results: dict[int, R] = {}
    with ThreadPoolExecutor(max_workers=effective_workers) as executor:
        futures = {
            executor.submit(process, spec): idx for idx, spec in enumerate(specs)
        }
        for future in as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()
    return [results[i] for i in range(len(specs))]
