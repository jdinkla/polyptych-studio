"""Mock text and image clients for anime pipeline testing."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class MockTextClient:
    """Drop-in replacement for TextClient that dispatches pre-registered responses by task name.

    Usage:
        client = MockTextClient()
        client.register_structured("a0", my_a0_output)
        client.register_text("a0r", "detailed description...")

    The mock records every call so tests can assert which code paths executed.
    """

    def __init__(self) -> None:
        self.provider_name = "gemini"
        self._structured: dict[str, list] = defaultdict(list)
        self._text: dict[str, list] = defaultdict(list)
        self._errors: dict[str, Exception] = {}
        self._repeat: dict[str, bool] = {}
        self._counts: dict[str, int] = defaultdict(int)
        self._calls: list[dict] = []

    # ── Registration ──

    def register_structured(
        self,
        task: str,
        response: BaseModel,
        *,
        repeat: bool = False,
    ) -> None:
        """Register a structured response for a task.

        Args:
            task: Task name (e.g. "a0", "a0_critique").
            response: Pydantic model instance to return.
            repeat: If True, reuse the same response on every call instead of popping.
        """
        self._structured[task].append(response)
        if repeat:
            self._repeat[f"structured:{task}"] = True

    def register_text(
        self,
        task: str,
        response: str,
        *,
        repeat: bool = False,
    ) -> None:
        """Register a text response for a task.

        Args:
            task: Task name (e.g. "a0r", "anime_enrichment").
            response: Text string to return.
            repeat: If True, reuse the same response on every call.
        """
        self._text[task].append(response)
        if repeat:
            self._repeat[f"text:{task}"] = True

    def register_error(self, task: str, error: Exception) -> None:
        """Register an error to raise for a task (both structured and text)."""
        self._errors[task] = error

    # ── Call counting ──

    def call_count(self, key: str) -> int:
        """Return the number of times a specific key was called.

        Key format: "structured:{task}" or "text:{task}".
        """
        return self._counts[key]

    def total_calls(self) -> int:
        """Return total number of calls across all tasks."""
        return sum(self._counts.values())

    # ── Call argument capture ──

    def last_call(self, task: str) -> dict:
        """Return the most recent call record for a task."""
        for call in reversed(self._calls):
            if call["task"] == task:
                return call
        raise ValueError(f"MockTextClient: no calls recorded for task={task!r}")

    def calls_for(self, task: str) -> list[dict]:
        """Return all call records for a task."""
        return [c for c in self._calls if c["task"] == task]

    # ── TextClient interface ──

    def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        model: str,
        system_instruction: str | None = None,
        max_output_tokens: int | None = None,
        task: str | None = None,
    ) -> T:
        key = f"structured:{task}"
        self._counts[key] += 1
        self._calls.append(
            {
                "task": task,
                "prompt": prompt,
                "response_schema": response_schema,
                "model": model,
                "system_instruction": system_instruction,
            }
        )

        if task in self._errors:
            raise self._errors[task]

        queue = self._structured.get(task, [])
        if not queue:
            raise ValueError(
                f"MockTextClient: no structured response registered for task={task!r}. "
                f"Registered tasks: {sorted(self._structured.keys())}"
            )

        if self._repeat.get(key):
            return queue[0]
        return queue.pop(0)

    def generate_text(
        self,
        prompt: str,
        model: str,
        system_instruction: str | None = None,
        task: str | None = None,
    ) -> str:
        key = f"text:{task}"
        self._counts[key] += 1

        if task in self._errors:
            raise self._errors[task]

        queue = self._text.get(task, [])
        if not queue:
            raise ValueError(
                f"MockTextClient: no text response registered for task={task!r}. "
                f"Registered tasks: {sorted(self._text.keys())}"
            )

        if self._repeat.get(key):
            return queue[0]
        return queue.pop(0)


class MockImageClient:
    """Minimal mock for ImageClient that writes a 1x1 PNG to the output directory."""

    def __init__(self) -> None:
        import threading
        self._call_count = 0
        self._lock = threading.Lock()

    def generate_image(self, prompt, output_dir: Path, **kwargs) -> Path:
        with self._lock:
            self._call_count += 1
            n = self._call_count
        output_dir.mkdir(parents=True, exist_ok=True)
        # Use uuid to avoid filename collisions across concurrent calls — the
        # caller renames the returned path, so collisions before rename matter.
        import uuid
        path = output_dir / f"mock-{n:03d}-{uuid.uuid4().hex[:8]}.png"
        # Minimal valid 1x1 PNG (67 bytes)
        path.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
            b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00"
            b"\x00\x00\x00IEND\xaeB`\x82"
        )
        return path
