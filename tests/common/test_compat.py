"""Tests for common.compat — env-var and runtime-dir backward-compat helpers."""

import logging

import pytest

from common import compat
from common.compat import (
    getenv_compat,
    resolve_runtime_file,
    runtime_dirs,
    runtime_write_dir,
)


@pytest.fixture(autouse=True)
def _reset_warn_cache():
    """The one-time-warning cache is module-global; clear it between tests."""
    compat._warned_env.clear()
    yield
    compat._warned_env.clear()


# --- getenv_compat ---


class TestGetenvCompat:
    def test_new_name_used(self, monkeypatch):
        monkeypatch.setenv("POLYPTYCH_MODEL", "gpt-new")
        monkeypatch.delenv("SLIDE_GEN_MODEL", raising=False)
        assert getenv_compat("POLYPTYCH_MODEL", "SLIDE_GEN_MODEL") == "gpt-new"

    def test_old_name_fallback_honored(self, monkeypatch):
        monkeypatch.delenv("POLYPTYCH_MODEL", raising=False)
        monkeypatch.setenv("SLIDE_GEN_MODEL", "gpt-legacy")
        assert getenv_compat("POLYPTYCH_MODEL", "SLIDE_GEN_MODEL") == "gpt-legacy"

    def test_new_takes_precedence_over_old(self, monkeypatch):
        monkeypatch.setenv("POLYPTYCH_MODEL", "gpt-new")
        monkeypatch.setenv("SLIDE_GEN_MODEL", "gpt-legacy")
        assert getenv_compat("POLYPTYCH_MODEL", "SLIDE_GEN_MODEL") == "gpt-new"

    def test_default_when_neither_set(self, monkeypatch):
        monkeypatch.delenv("POLYPTYCH_MODEL", raising=False)
        monkeypatch.delenv("SLIDE_GEN_MODEL", raising=False)
        assert getenv_compat("POLYPTYCH_MODEL", "SLIDE_GEN_MODEL") is None
        assert (
            getenv_compat("POLYPTYCH_MODEL", "SLIDE_GEN_MODEL", "fallback")
            == "fallback"
        )

    def test_empty_string_counts_as_set(self, monkeypatch):
        # Matches os.environ.get semantics: "" is set, not absent.
        monkeypatch.setenv("POLYPTYCH_MODEL", "")
        monkeypatch.setenv("SLIDE_GEN_MODEL", "gpt-legacy")
        assert getenv_compat("POLYPTYCH_MODEL", "SLIDE_GEN_MODEL", "d") == ""

    def test_deprecation_warning_on_old_name(self, monkeypatch, caplog):
        monkeypatch.delenv("POLYPTYCH_MODEL", raising=False)
        monkeypatch.setenv("SLIDE_GEN_MODEL", "gpt-legacy")
        with caplog.at_level(logging.WARNING, logger="polyptych"):
            getenv_compat("POLYPTYCH_MODEL", "SLIDE_GEN_MODEL")
        assert any(
            "SLIDE_GEN_MODEL" in r.message and "deprecated" in r.message
            for r in caplog.records
        )

    def test_deprecation_warning_fires_once(self, monkeypatch, caplog):
        monkeypatch.delenv("POLYPTYCH_MODEL", raising=False)
        monkeypatch.setenv("SLIDE_GEN_MODEL", "gpt-legacy")
        with caplog.at_level(logging.WARNING, logger="polyptych"):
            getenv_compat("POLYPTYCH_MODEL", "SLIDE_GEN_MODEL")
            getenv_compat("POLYPTYCH_MODEL", "SLIDE_GEN_MODEL")
            getenv_compat("POLYPTYCH_MODEL", "SLIDE_GEN_MODEL")
        warnings = [r for r in caplog.records if "SLIDE_GEN_MODEL" in r.message]
        assert len(warnings) == 1

    def test_new_name_does_not_warn(self, monkeypatch, caplog):
        monkeypatch.setenv("POLYPTYCH_MODEL", "gpt-new")
        with caplog.at_level(logging.WARNING, logger="polyptych"):
            getenv_compat("POLYPTYCH_MODEL", "SLIDE_GEN_MODEL")
        assert not caplog.records


# --- runtime dir resolution ---


class TestRuntimeDirs:
    def test_runtime_dirs_new_and_legacy(self, monkeypatch, tmp_path):
        monkeypatch.setattr(compat.Path, "home", classmethod(lambda cls: tmp_path))
        new, legacy = runtime_dirs("config")
        assert new == tmp_path / ".config" / "polyptych"
        assert legacy == tmp_path / ".config" / "slide-analysis"

    def test_cache_kind_uses_dot_cache(self, monkeypatch, tmp_path):
        monkeypatch.setattr(compat.Path, "home", classmethod(lambda cls: tmp_path))
        new, legacy = runtime_dirs("cache")
        assert new == tmp_path / ".cache" / "polyptych"
        assert legacy == tmp_path / ".cache" / "slide-analysis"

    def test_resolve_prefers_new(self, monkeypatch, tmp_path):
        monkeypatch.setattr(compat.Path, "home", classmethod(lambda cls: tmp_path))
        new = tmp_path / ".config" / "polyptych"
        legacy = tmp_path / ".config" / "slide-analysis"
        new.mkdir(parents=True)
        legacy.mkdir(parents=True)
        (new / "secrets.json").write_text("new")
        (legacy / "secrets.json").write_text("legacy")
        resolved = resolve_runtime_file("config", "secrets.json")
        assert resolved == new / "secrets.json"

    def test_resolve_falls_back_to_legacy(self, monkeypatch, tmp_path):
        monkeypatch.setattr(compat.Path, "home", classmethod(lambda cls: tmp_path))
        legacy = tmp_path / ".config" / "slide-analysis"
        legacy.mkdir(parents=True)
        (legacy / "secrets.json").write_text("legacy")
        resolved = resolve_runtime_file("config", "secrets.json")
        assert resolved == legacy / "secrets.json"

    def test_resolve_returns_none_when_absent(self, monkeypatch, tmp_path):
        monkeypatch.setattr(compat.Path, "home", classmethod(lambda cls: tmp_path))
        assert resolve_runtime_file("config", "secrets.json") is None

    def test_write_dir_defaults_to_new(self, monkeypatch, tmp_path):
        monkeypatch.setattr(compat.Path, "home", classmethod(lambda cls: tmp_path))
        assert runtime_write_dir("config") == tmp_path / ".config" / "polyptych"

    def test_write_dir_keeps_legacy_when_only_legacy_exists(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(compat.Path, "home", classmethod(lambda cls: tmp_path))
        legacy = tmp_path / ".config" / "slide-analysis"
        legacy.mkdir(parents=True)
        assert runtime_write_dir("config") == legacy

    def test_write_dir_prefers_new_when_both_exist(self, monkeypatch, tmp_path):
        monkeypatch.setattr(compat.Path, "home", classmethod(lambda cls: tmp_path))
        new = tmp_path / ".config" / "polyptych"
        legacy = tmp_path / ".config" / "slide-analysis"
        new.mkdir(parents=True)
        legacy.mkdir(parents=True)
        assert runtime_write_dir("config") == new
