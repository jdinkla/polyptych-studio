"""Tests for the shared image-batch-generation engine.

Covers the behavior the per-pipeline image loops relied on before they were
consolidated: skip-existing logic, per-item failure isolation, ref routing,
interleaved chunking, resume work-item building, and concurrent execution
with thread-local clients.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from polyptych.image_batch import (
    BatchItem,
    BatchResult,
    BatchSettings,
    BuiltPrompt,
    ImageBatchGenerator,
    ImageFailure,
)

from .mock_client import MockImageClient


class RecordingImageClient(MockImageClient):
    """MockImageClient that records which generate method served each call."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []
        self.threads: set[str] = set()

    def generate_image(self, prompt, output_dir: Path, **kwargs) -> Path:
        self.calls.append("generate_image")
        self.threads.add(threading.current_thread().name)
        return super().generate_image(prompt, output_dir, **kwargs)

    def generate_image_with_references(
        self, prompt, reference_images, output_dir: Path, **kwargs
    ) -> Path:
        self.calls.append("generate_image_with_references")
        self.threads.add(threading.current_thread().name)
        return super().generate_image(prompt, output_dir, **kwargs)


def make_batch(
    tmp_path: Path,
    client: MockImageClient | None = None,
    build_prompt=None,
    label: str = "slide",
    client_factory=None,
    failure_sink: list[ImageFailure] | None = None,
) -> ImageBatchGenerator:
    client = client or MockImageClient()
    return ImageBatchGenerator(
        client_factory=client_factory or (lambda: client),
        images_dir=tmp_path / "images",
        label=label,
        build_prompt=build_prompt or (lambda payload: BuiltPrompt(prompt=payload)),
        settings=BatchSettings(),
        failure_sink=failure_sink,
    )


def make_items(count: int) -> list[BatchItem]:
    return [
        BatchItem(index=i, item_id=f"slide-{i:02d}", payload={"n": i})
        for i in range(1, count + 1)
    ]


# =============================================================================
# Sequential mode
# =============================================================================


class TestRunSequential:
    def test_generates_and_renames_to_item_id(self, tmp_path: Path):
        batch = make_batch(tmp_path)
        result = batch.run_sequential(make_items(3))

        assert sorted(p.name for p in result.generated) == [
            "slide-01.png",
            "slide-02.png",
            "slide-03.png",
        ]
        assert all(p.exists() for p in result.generated)
        assert result.failed == []
        assert result.skipped == 0

    def test_skip_existing_skips_and_counts(self, tmp_path: Path):
        client = RecordingImageClient()
        batch = make_batch(tmp_path, client=client)
        (tmp_path / "images").mkdir(exist_ok=True)
        (tmp_path / "images" / "slide-02.png").write_bytes(b"existing")

        result = batch.run_sequential(make_items(3), skip_existing=True)

        assert result.skipped == 1
        assert len(result.generated) == 2
        assert len(client.calls) == 2

    def test_without_skip_existing_regenerates(self, tmp_path: Path):
        client = RecordingImageClient()
        batch = make_batch(tmp_path, client=client)
        (tmp_path / "images").mkdir(exist_ok=True)
        (tmp_path / "images" / "slide-02.png").write_bytes(b"existing")

        result = batch.run_sequential(make_items(3))

        assert result.skipped == 0
        assert len(client.calls) == 3
        assert len(result.generated) == 3

    def test_failure_isolated_with_type_and_message(self, tmp_path: Path):
        class FlakyClient(MockImageClient):
            def generate_image(self, prompt, output_dir, **kwargs):
                if prompt["n"] == 2:
                    raise RuntimeError("provider 500")
                return super().generate_image(prompt, output_dir, **kwargs)

        batch = make_batch(tmp_path, client=FlakyClient())
        result = batch.run_sequential(make_items(3))

        assert len(result.generated) == 2
        assert result.failed == [(2, "RuntimeError: provider 500")]

    def test_build_prompt_failure_is_also_isolated(self, tmp_path: Path):
        def build(payload) -> BuiltPrompt:
            if payload["n"] == 1:
                raise KeyError("missing section")
            return BuiltPrompt(prompt=payload)

        batch = make_batch(tmp_path, build_prompt=build)
        result = batch.run_sequential(make_items(2))

        assert len(result.generated) == 1
        assert result.failed[0][0] == 1
        assert "KeyError" in result.failed[0][1]


class TestRefRouting:
    def test_ref_paths_none_uses_plain_generate(self, tmp_path: Path):
        client = RecordingImageClient()
        batch = make_batch(
            tmp_path,
            client=client,
            build_prompt=lambda p: BuiltPrompt(prompt=p, ref_paths=None),
        )
        batch.run_sequential(make_items(1))
        assert client.calls == ["generate_image"]

    def test_empty_ref_list_falls_back_to_plain_generate(self, tmp_path: Path):
        client = RecordingImageClient()
        batch = make_batch(
            tmp_path,
            client=client,
            build_prompt=lambda p: BuiltPrompt(prompt=p, ref_paths=[]),
        )
        batch.run_sequential(make_items(1))
        assert client.calls == ["generate_image"]

    def test_nonempty_refs_use_reference_generation(self, tmp_path: Path):
        ref = tmp_path / "ref.png"
        ref.write_bytes(b"ref")
        client = RecordingImageClient()
        batch = make_batch(
            tmp_path,
            client=client,
            build_prompt=lambda p: BuiltPrompt(prompt=p, ref_paths=[ref]),
        )
        batch.run_sequential(make_items(1))
        assert client.calls == ["generate_image_with_references"]


class TestReport:
    def test_report_emits_counts_and_failures(self, tmp_path: Path, capsys):
        batch = make_batch(tmp_path, label="frame")
        result = BatchResult(
            generated=[tmp_path / "frame-001.png"],
            failed=[(2, "RuntimeError: boom")],
            skipped=3,
        )
        batch.report(result)
        out = capsys.readouterr().out
        assert "Skipped 3 existing image(s)" in out
        assert "Generated: 1, Failed: 1" in out
        assert "Frame 2: RuntimeError: boom" in out


# =============================================================================
# Interleaved mode
# =============================================================================


class TestRunInterleaved:
    def test_chunks_cover_all_items_and_collect_payloads(self, tmp_path: Path):
        batch = make_batch(tmp_path)
        payloads, result = batch.run_interleaved(iter(make_items(5)), chunk_size=2)

        assert [p["n"] for p in payloads] == [1, 2, 3, 4, 5]
        assert len(result.generated) == 5

    def test_select_collects_payload_without_image(self, tmp_path: Path):
        client = RecordingImageClient()
        batch = make_batch(tmp_path, client=client)
        payloads, result = batch.run_interleaved(
            iter(make_items(4)),
            chunk_size=2,
            select=lambda item: item.index in (2, 4),
        )

        # All payloads collected (aggregate YAMLs stay complete) …
        assert [p["n"] for p in payloads] == [1, 2, 3, 4]
        # … but only the selected items produced images.
        assert sorted(p.name for p in result.generated) == [
            "slide-02.png",
            "slide-04.png",
        ]
        assert len(client.calls) == 2

    def test_skip_existing_applies_per_chunk(self, tmp_path: Path):
        batch = make_batch(tmp_path)
        (tmp_path / "images").mkdir(exist_ok=True)
        (tmp_path / "images" / "slide-03.png").write_bytes(b"existing")

        payloads, result = batch.run_interleaved(
            iter(make_items(4)), chunk_size=2, skip_existing=True
        )

        assert len(payloads) == 4
        assert result.skipped == 1
        assert len(result.generated) == 3


# =============================================================================
# Concurrent mode
# =============================================================================


class TestBuildPreloadedWorkItems:
    def test_skips_existing_images(self, tmp_path: Path):
        batch = make_batch(tmp_path)
        (tmp_path / "images").mkdir(exist_ok=True)
        (tmp_path / "images" / "slide-01.png").write_bytes(b"existing")

        work_items, skipped = batch.build_preloaded_work_items(make_items(3))

        assert skipped == 1
        assert [w.index for w in work_items] == [2, 3]
        # Prompt payload is pre-loaded so producers are no-ops.
        assert all(w.prompt is not None for w in work_items)

    def test_force_includes_everything(self, tmp_path: Path):
        batch = make_batch(tmp_path)
        (tmp_path / "images").mkdir(exist_ok=True)
        (tmp_path / "images" / "slide-01.png").write_bytes(b"existing")

        work_items, skipped = batch.build_preloaded_work_items(
            make_items(3), force=True
        )

        assert skipped == 0
        assert len(work_items) == 3


class TestBuildResumableWorkItems:
    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        (tmp_path / "images").mkdir(exist_ok=True)
        (tmp_path / "prompts").mkdir()
        return tmp_path

    def _load_yaml(self, output_dir: Path):
        import yaml

        def load(rel: str) -> dict | None:
            path = output_dir / rel
            if path.exists():
                return yaml.safe_load(path.read_text())
            return None

        return load

    def test_classifies_skipped_preloaded_and_from_scratch(self, output_dir: Path):
        batch = make_batch(output_dir)
        # slide-01: prompt + image → skipped
        (output_dir / "prompts" / "slide-01-prompt.yaml").write_text("n: 1")
        (output_dir / "images" / "slide-01.png").write_bytes(b"img")
        # slide-02: prompt only → preloaded
        (output_dir / "prompts" / "slide-02-prompt.yaml").write_text("n: 2")
        # slide-03: nothing → from scratch

        work_items, skipped, preloaded, from_scratch = batch.build_resumable_work_items(
            make_items(3),
            force=False,
            load_yaml=self._load_yaml(output_dir),
            parse_prompt=lambda loaded, index: loaded,
        )

        assert (skipped, preloaded, from_scratch) == (1, 1, 1)
        assert [w.index for w in work_items] == [2, 3]
        assert work_items[0].prompt == {"n": 2}
        assert work_items[1].prompt is None

    def test_parse_prompt_hook_transforms_loaded_yaml(self, output_dir: Path):
        batch = make_batch(output_dir)
        (output_dir / "prompts" / "slide-01-prompt.yaml").write_text("n: 1")

        work_items, *_ = batch.build_resumable_work_items(
            make_items(1),
            force=False,
            load_yaml=self._load_yaml(output_dir),
            parse_prompt=lambda loaded, index: ("parsed", index, loaded),
        )

        assert work_items[0].prompt == ("parsed", 1, {"n": 1})

    def test_force_regenerates_all(self, output_dir: Path):
        batch = make_batch(output_dir)
        (output_dir / "prompts" / "slide-01-prompt.yaml").write_text("n: 1")
        (output_dir / "images" / "slide-01.png").write_bytes(b"img")

        work_items, skipped, preloaded, from_scratch = batch.build_resumable_work_items(
            make_items(1),
            force=True,
            load_yaml=self._load_yaml(output_dir),
            parse_prompt=lambda loaded, index: loaded,
        )

        assert (skipped, preloaded, from_scratch) == (0, 0, 1)
        assert len(work_items) == 1
        assert work_items[0].prompt is None  # produced from scratch


class TestLogResume:
    def test_false_when_nothing_to_do(self, tmp_path: Path, capsys):
        batch = make_batch(tmp_path)
        assert batch.log_resume([], 3) is False
        assert "All 3 slides already complete" in capsys.readouterr().out

    def test_true_with_remaining_work(self, tmp_path: Path, capsys):
        batch = make_batch(tmp_path)
        work_items, _ = batch.build_preloaded_work_items(make_items(2))
        assert batch.log_resume(work_items, 1) is True
        out = capsys.readouterr().out
        assert "Resume: 1 already complete, 2 remaining" in out
        assert "Processing 2 of 3 slides" in out


class TestRunConcurrent:
    def test_generates_all_items(self, tmp_path: Path):
        batch = make_batch(tmp_path)
        work_items, _ = batch.build_preloaded_work_items(make_items(4))

        result = batch.run_concurrent(work_items, num_consumers=2)

        assert len(result.completed) == 4
        assert result.failed == []
        images = sorted((tmp_path / "images").glob("slide-*.png"))
        assert len(images) == 4

    def test_one_client_per_consumer_thread(self, tmp_path: Path):
        clients: list[RecordingImageClient] = []

        def factory() -> RecordingImageClient:
            client = RecordingImageClient()
            clients.append(client)
            return client

        batch = make_batch(tmp_path, client_factory=factory)
        work_items, _ = batch.build_preloaded_work_items(make_items(6))
        batch.run_concurrent(work_items, num_consumers=3)

        # At most one client per consumer thread, each used from one thread only.
        assert 1 <= len(clients) <= 3
        assert all(len(c.threads) == 1 for c in clients)

    def test_consume_failure_reported_per_item(self, tmp_path: Path):
        class FlakyClient(MockImageClient):
            def generate_image(self, prompt, output_dir, **kwargs):
                if prompt["n"] == 2:
                    raise RuntimeError("provider 500")
                return super().generate_image(prompt, output_dir, **kwargs)

        batch = make_batch(tmp_path, client=FlakyClient())
        work_items, _ = batch.build_preloaded_work_items(make_items(3))
        result = batch.run_concurrent(work_items, num_consumers=2)

        assert len(result.completed) == 2
        assert len(result.failed) == 1
        assert result.failed[0][0] == 2

    def test_produce_fn_runs_before_consume(self, tmp_path: Path):
        batch = make_batch(tmp_path)
        work_items, _ = batch.build_preloaded_work_items(make_items(2))
        for w in work_items:
            w.prompt = None  # force producers to fill prompts

        def produce(item) -> None:
            item.prompt = {"n": item.index}

        result = batch.run_concurrent(
            work_items, num_consumers=2, num_producers=2, produce_fn=produce
        )

        assert len(result.completed) == 2


# =============================================================================
# Run-level failure aggregation (failure_sink)
# =============================================================================


class _FlakyClient(MockImageClient):
    """Fails item n=2 on every call."""

    def generate_image(self, prompt, output_dir, **kwargs):
        if prompt["n"] == 2:
            raise RuntimeError("provider 500")
        return super().generate_image(prompt, output_dir, **kwargs)


class TestFailureSink:
    def test_sequential_failure_recorded_with_label(self, tmp_path: Path):
        sink: list[ImageFailure] = []
        batch = make_batch(
            tmp_path, client=_FlakyClient(), label="scene", failure_sink=sink
        )
        batch.run_sequential(make_items(3))

        assert len(sink) == 1
        assert sink[0].label == "scene"
        assert sink[0].index == 2
        assert sink[0].error == "RuntimeError: provider 500"
        assert str(sink[0]) == "Scene 2: RuntimeError: provider 500"

    def test_success_and_skips_leave_sink_empty(self, tmp_path: Path):
        sink: list[ImageFailure] = []
        batch = make_batch(tmp_path, failure_sink=sink)
        (tmp_path / "images").mkdir(exist_ok=True)
        (tmp_path / "images" / "slide-01.png").write_bytes(b"existing")

        batch.run_sequential(make_items(2), skip_existing=True)

        assert sink == []

    def test_concurrent_failure_recorded(self, tmp_path: Path):
        sink: list[ImageFailure] = []
        batch = make_batch(tmp_path, client=_FlakyClient(), failure_sink=sink)
        work_items, _ = batch.build_preloaded_work_items(make_items(3))
        batch.run_concurrent(work_items, num_consumers=2)

        assert len(sink) == 1
        assert sink[0].index == 2
        assert "provider 500" in sink[0].error

    def test_resume_after_partial_failure_regenerates_only_missing(
        self, tmp_path: Path
    ):
        sink: list[ImageFailure] = []
        batch = make_batch(tmp_path, client=_FlakyClient(), failure_sink=sink)
        first = batch.run_sequential(make_items(3), skip_existing=True)
        assert len(first.generated) == 2
        assert len(sink) == 1

        # Retry run with a healthy client: only the missing item is generated.
        retry_sink: list[ImageFailure] = []
        retry_client = RecordingImageClient()
        retry = make_batch(tmp_path, client=retry_client, failure_sink=retry_sink)
        second = retry.run_sequential(make_items(3), skip_existing=True)

        assert second.skipped == 2
        assert len(second.generated) == 1
        assert second.generated[0].name == "slide-02.png"
        assert len(retry_client.calls) == 1
        assert retry_sink == []
