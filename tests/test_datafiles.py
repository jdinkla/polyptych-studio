"""Tests for packaged-data resolution (:mod:`polyptych._datafiles`).

These guard the wheel-install code path: when ``polyptych/_data/`` exists the
loaders must read from it, not from the repo root. Dev/editable runs never hit
that branch (the bundled dir is absent), so without these tests a broken
``force-include`` mapping would only surface after publishing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polyptych import _datafiles


def _build_bundled_data(root: Path) -> Path:
    """Create a minimal ``_data`` tree mirroring the wheel's force-include layout."""
    data = root / "_data"
    (data / "prompts" / "tasks").mkdir(parents=True)
    (data / "prompts" / "providers").mkdir(parents=True)
    (data / "model_config.yaml").write_text(
        "providers:\n  gemini:\n    fast: m\ntasks:\n  task1: fast\n"
    )
    (data / "image_model_config.yaml").write_text("providers:\n  gemini: img-m\n")
    (data / "image-presets.yaml").write_text("gem: {provider: gemini}\n")
    (data / "pipeline-presets.yaml").write_text("slide:\n  fast: {concurrent: 4}\n")
    (data / "prompts" / "tasks" / "task-01-genre-classification.md").write_text("P1")
    (data / "prompts" / "providers" / "gemini-best-practices.md").write_text("G")
    return data


@pytest.fixture
def bundled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point :func:`_datafiles.data_root` at a simulated bundled ``_data`` dir."""
    data = _build_bundled_data(tmp_path)
    monkeypatch.setattr(_datafiles, "_BUNDLED_DATA", data)
    return data


def test_data_root_prefers_bundled_dir_when_present(bundled: Path) -> None:
    assert _datafiles.data_root() == bundled


def test_data_root_falls_back_to_repo_root(monkeypatch: pytest.MonkeyPatch) -> None:
    # A non-existent bundled dir => editable/source layout, two parents up.
    monkeypatch.setattr(_datafiles, "_BUNDLED_DATA", Path("/nonexistent/_data"))
    assert _datafiles.data_root() == _datafiles._PKG_DIR.parent.parent


def test_loaders_read_from_bundled_data(bundled: Path) -> None:
    from polyptych.model_config import load_image_model_config, load_model_config
    from polyptych.prompt_loader import get_prompts_dir, load_provider_guidelines

    assert load_model_config().tasks == {"task1": "fast"}
    assert load_image_model_config().providers == {"gemini": "img-m"}
    assert get_prompts_dir() == bundled / "prompts" / "tasks"
    assert load_provider_guidelines("gemini") == "G"


def test_presets_read_from_bundled_data(bundled: Path) -> None:
    from polyptych.presets import load_image_preset, load_pipeline_preset

    assert load_image_preset("gem") == {"provider": "gemini"}
    assert load_pipeline_preset("slide", "fast") == {"concurrent": 4}


def test_extension_model_configs_override_wheel_defaults(
    bundled, tmp_path, monkeypatch
):
    from polyptych import model_config as models

    monkeypatch.setattr(models, "_CONFIG_DIRS", [])
    extension = tmp_path / "extension"
    extension.mkdir()
    (extension / "model_config.yaml").write_text(
        "providers:\n  openai:\n    fast: gpt-5.6-terra\n    thinking: gpt-5.6-sol\n"
        "tasks:\n  custom_task: thinking\nthinking_budget:\n  custom_task: 16384\n"
    )
    models.register_model_config_dir(extension)
    monkeypatch.chdir(tmp_path)
    config = models.load_model_config()
    assert config.providers["openai"]["thinking"] == "gpt-5.6-sol"
    assert models.resolve_thinking_budget(config, "custom_task", "openai") == 16384
    assert models.load_model_config(override="override").providers["openai"] == {
        "fast": "override",
        "thinking": "override",
    }
    # Missing extension image config falls back independently to the wheel.
    assert models.load_image_model_config().providers == {"gemini": "img-m"}
    (extension / "image_model_config.yaml").write_text(
        "providers:\n  xai: grok-imagine-image-2.0\n"
    )
    assert models.load_image_model_config().providers == {
        "xai": "grok-imagine-image-2.0"
    }
    assert models.load_image_model_config(override="custom").providers == {
        "xai": "custom"
    }
