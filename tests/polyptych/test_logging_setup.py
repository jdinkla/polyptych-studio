"""Tests for polyptych.logging_setup."""

import logging
from pathlib import Path

import pytest

from polyptych.logging_setup import (
    LOGGER_NAME,
    configure_logging,
    reset_logging,
)


@pytest.fixture(autouse=True)
def _reset_between_tests():
    """Every test starts with a clean logger — the setup module is process-global."""
    reset_logging()
    yield
    reset_logging()


def _own_handlers(logger: logging.Logger) -> list[logging.Handler]:
    """Handlers installed by configure_logging, excluding pytest's capture handler.

    pytest >= 9.1 attaches its ``LogCaptureHandler`` directly to non-propagating
    loggers (configure_logging sets ``propagate=False``), which would otherwise
    inflate handler counts. Filter it out so these tests assert on our own
    handlers regardless of the pytest version.
    """
    return [h for h in logger.handlers if type(h).__name__ != "LogCaptureHandler"]


class TestLevelResolution:
    def test_defaults_to_info(self):
        logger = configure_logging()
        assert logger.level == logging.INFO

    def test_respects_env_var(self, monkeypatch):
        monkeypatch.setenv("POLYPTYCH_LOG_LEVEL", "DEBUG")
        logger = configure_logging()
        assert logger.level == logging.DEBUG

    def test_respects_deprecated_env_var(self, monkeypatch):
        monkeypatch.delenv("POLYPTYCH_LOG_LEVEL", raising=False)
        monkeypatch.setenv("SLIDE_GEN_LOG_LEVEL", "DEBUG")
        logger = configure_logging()
        assert logger.level == logging.DEBUG

    def test_new_env_var_wins_over_deprecated(self, monkeypatch):
        monkeypatch.setenv("POLYPTYCH_LOG_LEVEL", "ERROR")
        monkeypatch.setenv("SLIDE_GEN_LOG_LEVEL", "DEBUG")
        logger = configure_logging()
        assert logger.level == logging.ERROR

    def test_explicit_level_overrides_env(self, monkeypatch):
        monkeypatch.setenv("POLYPTYCH_LOG_LEVEL", "DEBUG")
        logger = configure_logging(level="WARNING", force=True)
        assert logger.level == logging.WARNING

    def test_accepts_integer_level(self):
        logger = configure_logging(level=logging.ERROR)
        assert logger.level == logging.ERROR

    def test_rejects_unknown_level_name(self):
        with pytest.raises(ValueError, match="Unknown log level"):
            configure_logging(level="BOGUS")


class TestHandlers:
    def test_installs_stderr_handler(self):
        logger = configure_logging()
        stream_handlers = [
            h
            for h in _own_handlers(logger)
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(stream_handlers) == 1

    def test_adds_file_handler_when_requested(self, tmp_path: Path):
        log_file = tmp_path / "polyptych.log"
        logger = configure_logging(log_file=log_file)
        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1
        assert Path(file_handlers[0].baseFilename) == log_file

    def test_log_file_actually_receives_records(self, tmp_path: Path):
        log_file = tmp_path / "out.log"
        logger = configure_logging(level="INFO", log_file=log_file)
        logger.info("hello world")
        # Flush the file handler so the write lands before we read
        for h in logger.handlers:
            h.flush()
        assert "hello world" in log_file.read_text()

    def test_does_not_propagate_to_root(self):
        logger = configure_logging()
        assert logger.propagate is False


class TestIdempotence:
    def test_second_call_without_force_is_ignored(self):
        first = configure_logging(level="DEBUG")
        assert first.level == logging.DEBUG
        second = configure_logging(level="ERROR")
        assert second is first
        assert first.level == logging.DEBUG  # unchanged

    def test_force_swaps_configuration(self):
        configure_logging(level="DEBUG")
        logger = logging.getLogger(LOGGER_NAME)
        handlers_before = _own_handlers(logger)
        configure_logging(level="ERROR", force=True)
        assert logger.level == logging.ERROR
        # Same count (new stderr handler replaced the old one); identity differs
        handlers_after = _own_handlers(logger)
        assert len(handlers_after) == len(handlers_before)
        assert handlers_after[0] is not handlers_before[0]


class TestChildLoggers:
    def test_child_loggers_inherit_handlers(self, capsys):
        configure_logging(level="INFO")
        child = logging.getLogger("polyptych.client")
        child.warning("fallback blocked")
        err = capsys.readouterr().err
        assert "fallback blocked" in err
        assert "WARNING" in err
        assert "polyptych.client" in err
