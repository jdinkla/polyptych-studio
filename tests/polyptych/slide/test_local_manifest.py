"""Manifest attribution survives local, partial CLI, and cached-image runs."""

from concurrent.futures import ThreadPoolExecutor

import pytest
import yaml

from polyptych.model_config import ImageModelConfig
from polyptych.models import TaskI2Output
from polyptych.provenance import read_task_provenance, record_task_provenance
from polyptych.providers.base import ContentBlockedError
from polyptych.run_config import InfographicRunConfig, SlideRunConfig

from ..test_client import FakeProvider
from ..test_pipeline_init import _build_pipeline
from ..test_pipeline_infographic import _i0, _i1, _variant
from ..mock_client import MockImageClient

LOCAL_MANIFEST = {
    "pipeline": "infographic",
    "mode": "local",
    "timestamp": "2026-06-13T00:00:00+00:00",
    "git_commit": "abc1234",
    "source": "source.md",
    "models": "gpt-6-astra",
    "tasks_completed": ["i0", "i1", "i2"],
    "editor_note": "Keep this",
}


def seed_local(pipeline):
    out = pipeline.output_dir
    (out / "manifest.yaml").write_text(yaml.safe_dump(LOCAL_MANIFEST))
    for filename, model in (
        ("task-i0-analysis.yaml", _i0()),
        ("task-i1-design.yaml", _i1()),
        ("task-i2-prompts.yaml", TaskI2Output(variants=[_variant()])),
    ):
        (out / filename).write_text(yaml.safe_dump(model.model_dump()))


@pytest.mark.parametrize("sidecar", [False, True])
def test_local_to_images_then_cached_resume(
    tmp_path, source_text, test_model_config, monkeypatch, sidecar
):
    pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
    seed_local(pipeline)
    if sidecar:
        for task in ("i0", "i1", "i2"):
            record_task_provenance(
                pipeline.output_dir, task, mode="local", model="gpt-6-astra"
            )
    texts = {p: p.read_bytes() for p in pipeline.output_dir.glob("task-*.yaml")}
    image_client = MockImageClient()
    monkeypatch.setattr(pipeline, "_make_image_client", lambda _: image_client)
    monkeypatch.setattr(
        pipeline.text_client,
        "_get_provider",
        lambda _: pytest.fail("Text call in image-only run"),
    )
    for image_model in ("gpt-image-2.5-flare", "gpt-image-2.5-sunburst"):
        pipeline.run_infographic_pipeline(
            InfographicRunConfig(
                from_step="images",
                provider="openai",
                image_model=image_model,
                quality="low",
                size="1536x1024",
                num_variants=1,
            )
        )
        manifest = yaml.safe_load((pipeline.output_dir / "manifest.yaml").read_text())
        assert manifest["models"] == "gpt-6-astra"
        assert manifest["mode"] == "local"
        assert manifest["image_model"] == image_model  # invocation configuration
        assert manifest["configured_models"]
        assert manifest["editor_note"] == "Keep this"
        assert set(manifest["task_provenance"]) == {"i0", "i1", "i2"}
    assert all(p.read_bytes() == data for p, data in texts.items())
    assert image_client._call_count == 1  # second run reused the first image


def test_partial_text_rerun_records_fallback_not_config(
    tmp_path, source_text, test_model_config
):
    pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
    seed_local(pipeline)
    client = pipeline.text_client
    client.usage_log = None  # provenance works even without JSONL logging
    client._fallback_chain = ["openai"]
    client.model_resolver = lambda task, provider: "actual-fallback-model"
    client._providers = {
        "gemini": FakeProvider("gemini", raise_blocked=ContentBlockedError("blocked")),
        "openai": FakeProvider("openai", structured_response=_i1()),
    }
    pipeline.run_infographic_pipeline(
        InfographicRunConfig(from_step="i1", to_step="i1", skip_images=True)
    )
    data = yaml.safe_load((pipeline.output_dir / "manifest.yaml").read_text())
    assert data["models"] == ["actual-fallback-model", "gpt-6-astra"]
    assert data["mode"] == "mixed"
    for task in ("i0", "i2"):
        assert data["task_provenance"][task]["model"] == "gpt-6-astra"
    entry = data["task_provenance"]["i1"]
    assert entry["model"] == "actual-fallback-model"
    assert entry["provider"] == "openai"
    assert entry["model_source"] == "response"
    # Another manifest write must not restore the overwritten local i1 entry.
    pipeline._write_manifest("infographic", InfographicRunConfig(from_step="images"))
    assert read_task_provenance(pipeline.output_dir)["i1"] == entry


@pytest.mark.parametrize(
    "legacy",
    [{}, {"models": ["unused-gemini"]}, {"models": "unused-gemini", "mode": "cli"}],
)
def test_missing_attribution_does_not_invent_authors(slide_pipeline, legacy):
    path = slide_pipeline.output_dir / "manifest.yaml"
    path.write_text(yaml.safe_dump(legacy))
    slide_pipeline._write_manifest("slide", SlideRunConfig(from_step="images"))
    result = yaml.safe_load(path.read_text())
    assert result["models"] == []
    if legacy:
        assert result["legacy_models"] == legacy["models"]


def test_sidecar_repairs_old_cli_manifest_and_preserves_unknown_fields(slide_pipeline):
    out = slide_pipeline.output_dir
    (out / "manifest.yaml").write_text("models: wrong-gemini\neditor_note: keep\n")
    record_task_provenance(out, "i0", mode="local", model="gpt-6-astra")
    record_task_provenance(out, "i1", mode="cli", model="legacy-configured")
    slide_pipeline.image_model_config = ImageModelConfig(
        providers={"openai": "configured-image"}
    )
    slide_pipeline._write_manifest(
        "infographic", InfographicRunConfig(provider="openai")
    )
    result = yaml.safe_load((out / "manifest.yaml").read_text())
    assert result["models"] == "gpt-6-astra"
    assert result["image_model"] == "configured-image"
    assert result["task_provenance"]["i1"]["model_source"] == "configured"
    assert result["editor_note"] == "keep"


def test_concurrent_task_records_do_not_drop_other_authors(tmp_path):
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(
            pool.map(
                lambda i: record_task_provenance(
                    tmp_path, f"task{i}", mode="local", model="gpt-6-astra"
                ),
                range(30),
            )
        )
    assert len(read_task_provenance(tmp_path)) == 30


def test_failed_call_leaves_local_author_intact(
    tmp_path, source_text, test_model_config
):
    pipeline = _build_pipeline(tmp_path, source_text, test_model_config)
    seed_local(pipeline)
    pipeline.text_client._providers = {
        "gemini": FakeProvider("gemini", raise_other=RuntimeError("offline")),
    }
    with pytest.raises(RuntimeError, match="offline"):
        pipeline.run_task_i1(_i0())
    assert read_task_provenance(pipeline.output_dir)["i1"]["model"] == "gpt-6-astra"
    assert not (pipeline.output_dir / "provenance.yaml").exists()
