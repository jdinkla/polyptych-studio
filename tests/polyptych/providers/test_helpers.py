"""Tests for provider helper functions that don't require live SDK calls.

Each provider exposes a handful of static-ish helpers for extracting usage,
detecting refusals, and building request kwargs. These are the pieces most
likely to drift when upstream SDK response shapes change — so they're
worth covering explicitly with synthetic response objects.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from polyptych.providers import openai as openai_mod
from polyptych.providers import xai as xai_mod
from polyptych.providers.anthropic import AnthropicTextProvider
from polyptych.providers.base import (
    ContentBlockedError,
    TextGenerationResult,
    TransientProviderError,
)
from polyptych.providers.gemini import GeminiTextProvider
from polyptych.providers.openai import OpenAITextProvider
from polyptych.providers.xai import XAITextProvider


class _Reply(BaseModel):
    answer: str


# ---------------------------------------------------------------------------
# Synthetic response factories — each mimics the shape of the SDK's response
# object closely enough to exercise _extract_result / _check_content_blocked.
# ---------------------------------------------------------------------------


def _anthropic_response(
    input_tokens: int = 100,
    output_tokens: int = 50,
    stop_reason: str = "end_turn",
    content_blocks=None,
):
    if content_blocks is None:
        content_blocks = [SimpleNamespace(type="text", text="hello")]
    return SimpleNamespace(
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
        stop_reason=stop_reason,
        content=content_blocks,
    )


def _openai_response(
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    finish_reason: str = "stop",
    refusal: str | None = None,
    content: str | None = "{}",
):
    message = SimpleNamespace(content=content, refusal=refusal)
    choice = SimpleNamespace(finish_reason=finish_reason, message=message)
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    return SimpleNamespace(choices=[choice], usage=usage)


def _gemini_response(
    prompt_tokens: int = 100,
    output_tokens: int = 50,
    total_tokens: int | None = None,
    thoughts: int | None = None,
):
    total = total_tokens if total_tokens is not None else prompt_tokens + output_tokens
    meta = SimpleNamespace(
        prompt_token_count=prompt_tokens,
        candidates_token_count=output_tokens,
        total_token_count=total,
        thoughts_token_count=thoughts,
    )
    return SimpleNamespace(usage_metadata=meta)


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------


class TestAnthropicHelpers:
    def test_extract_result_populates_usage(self):
        resp = _anthropic_response(input_tokens=120, output_tokens=30)
        result = AnthropicTextProvider._extract_result(resp, "claude-test", 1.25)
        assert isinstance(result, TextGenerationResult)
        assert result.provider == "anthropic"
        assert result.model == "claude-test"
        assert result.duration_s == 1.25
        assert result.prompt_token_count == 120
        assert result.candidates_token_count == 30
        assert result.total_token_count == 150

    def test_extract_result_handles_missing_usage(self):
        resp = SimpleNamespace(content=[], stop_reason="end_turn")
        result = AnthropicTextProvider._extract_result(resp, "claude-test", 0.1)
        assert result.prompt_token_count is None
        assert result.candidates_token_count is None

    def test_check_content_blocked_passes_on_normal_stop(self):
        resp = _anthropic_response(stop_reason="end_turn")
        # No raise expected.
        AnthropicTextProvider._check_content_blocked(resp, "claude-test")

    def test_check_content_blocked_raises_on_refusal(self):
        resp = _anthropic_response(stop_reason="refusal")
        with pytest.raises(ContentBlockedError) as excinfo:
            AnthropicTextProvider._check_content_blocked(resp, "claude-test")
        assert excinfo.value.block_reason == "refusal"

    def test_extract_text_joins_text_blocks(self):
        resp = SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text="Hello "),
                SimpleNamespace(type="thinking", text="<should be skipped>"),
                SimpleNamespace(type="text", text="world"),
            ]
        )
        assert AnthropicTextProvider._extract_text(resp) == "Hello world"

    def test_extract_text_empty_when_only_thinking(self):
        resp = SimpleNamespace(
            content=[
                SimpleNamespace(type="thinking", text="hidden"),
            ]
        )
        assert AnthropicTextProvider._extract_text(resp) == ""

    def test_build_kwargs_minimal(self):
        kwargs = AnthropicTextProvider._build_kwargs(
            "claude-test",
            [{"role": "user", "content": "hi"}],
            None,
            None,
            None,
        )
        assert kwargs["model"] == "claude-test"
        assert kwargs["max_tokens"] == 16384  # DEFAULT_MAX_TOKENS
        assert "system" not in kwargs
        assert "thinking" not in kwargs

    def test_build_kwargs_with_system_instruction(self):
        kwargs = AnthropicTextProvider._build_kwargs(
            "m",
            [{"role": "user", "content": "hi"}],
            "be terse",
            None,
            None,
        )
        assert kwargs["system"] == "be terse"

    def test_build_kwargs_thinking_budget_bumps_max_tokens(self):
        # max_tokens of 1000 + thinking 4000 should be bumped to accommodate.
        kwargs = AnthropicTextProvider._build_kwargs(
            "m",
            [{"role": "user", "content": "hi"}],
            None,
            max_output_tokens=1000,
            thinking_budget=4000,
        )
        assert kwargs["thinking"] == {"type": "enabled", "budget_tokens": 4000}
        # max_tokens must be at least budget + 1024.
        assert kwargs["max_tokens"] >= 4000 + 1024

    def test_build_kwargs_respects_larger_max_when_thinking_small(self):
        kwargs = AnthropicTextProvider._build_kwargs(
            "m",
            [{"role": "user", "content": "hi"}],
            None,
            max_output_tokens=20000,
            thinking_budget=1000,
        )
        # If given max > thinking + 1024, keep the larger value.
        assert kwargs["max_tokens"] == 20000


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


class TestOpenAIHelpers:
    def test_extract_result_populates_usage(self):
        resp = _openai_response(prompt_tokens=80, completion_tokens=20)
        result = OpenAITextProvider._extract_result(resp, "gpt-test", 0.7)
        assert result.provider == "openai"
        assert result.prompt_token_count == 80
        assert result.candidates_token_count == 20
        assert result.total_token_count == 100

    def test_extract_result_handles_missing_usage(self):
        resp = SimpleNamespace(choices=[], usage=None)
        result = OpenAITextProvider._extract_result(resp, "gpt-test", 0.1)
        assert result.prompt_token_count is None

    def test_check_content_blocked_passes_on_normal_stop(self):
        resp = _openai_response(finish_reason="stop")
        OpenAITextProvider._check_content_blocked(resp, "gpt-test")

    def test_check_content_blocked_raises_on_content_filter(self):
        resp = _openai_response(finish_reason="content_filter")
        with pytest.raises(ContentBlockedError) as excinfo:
            OpenAITextProvider._check_content_blocked(resp, "gpt-test")
        assert excinfo.value.block_reason == "content_filter"

    def test_check_content_blocked_raises_on_refusal(self):
        resp = _openai_response(
            finish_reason="stop",
            refusal="I can't help with that",
        )
        with pytest.raises(ContentBlockedError) as excinfo:
            OpenAITextProvider._check_content_blocked(resp, "gpt-test")
        assert excinfo.value.block_reason == "refusal"
        assert "can't help" in str(excinfo.value)


# ---------------------------------------------------------------------------
# xAI (shares shape with OpenAI but names itself differently in messages)
# ---------------------------------------------------------------------------


class TestXAIHelpers:
    def test_extract_result_labels_as_xai(self):
        resp = _openai_response()
        result = XAITextProvider._extract_result(resp, "grok-test", 0.5)
        assert result.provider == "xai"
        assert result.prompt_token_count == 100

    def test_check_content_blocked_raises_on_content_filter(self):
        resp = _openai_response(finish_reason="content_filter")
        with pytest.raises(ContentBlockedError) as excinfo:
            XAITextProvider._check_content_blocked(resp, "grok-test")
        assert excinfo.value.block_reason == "content_filter"
        assert "xAI" in str(excinfo.value)

    def test_check_content_blocked_raises_on_refusal(self):
        resp = _openai_response(finish_reason="stop", refusal="nope")
        with pytest.raises(ContentBlockedError):
            XAITextProvider._check_content_blocked(resp, "grok-test")


# ---------------------------------------------------------------------------
# Shared generate_structured flow (base._generate_structured_with_retry),
# exercised through the OpenAI and xAI providers with _create mocked out.
# ---------------------------------------------------------------------------


def _stub_client(provider, monkeypatch):
    """Skip real API-key resolution / client construction."""
    monkeypatch.setattr(provider, "_get_client", lambda: object())


class TestOpenAIGenerateStructured:
    def test_returns_validated_model(self, monkeypatch):
        provider = OpenAITextProvider(api_key="k")
        _stub_client(provider, monkeypatch)
        resp = _openai_response(content='{"answer": "hi"}')
        monkeypatch.setattr(openai_mod, "_create", lambda client, **kw: resp)

        result, meta = provider.generate_structured("q", _Reply, "gpt-test")
        assert result.answer == "hi"
        assert meta.provider == "openai"
        assert meta.prompt_token_count == 100


class TestXAIGenerateStructured:
    def test_json_schema_success_no_warning(self, monkeypatch, caplog):
        provider = XAITextProvider(api_key="k")
        _stub_client(provider, monkeypatch)
        resp = _openai_response(content='{"answer": "ok"}')
        monkeypatch.setattr(xai_mod, "_create", lambda client, **kw: resp)

        with caplog.at_level(logging.WARNING, logger="polyptych.providers.xai"):
            result, _ = provider.generate_structured("q", _Reply, "grok-test")
        assert result.answer == "ok"
        assert caplog.records == []

    def test_fallback_logs_warning_with_model_and_exc(self, monkeypatch, caplog):
        provider = XAITextProvider(api_key="k")
        _stub_client(provider, monkeypatch)
        good = _openai_response(content='{"answer": "recovered"}')
        calls = {"n": 0}

        def fake_create(client, **kwargs):
            calls["n"] += 1
            # First call uses json_schema and fails; second (fallback) succeeds.
            if "response_format" in kwargs:
                raise ValueError("response_format not supported")
            return good

        monkeypatch.setattr(xai_mod, "_create", fake_create)

        with caplog.at_level(logging.WARNING, logger="polyptych.providers.xai"):
            result, _ = provider.generate_structured("q", _Reply, "grok-test")

        assert result.answer == "recovered"
        assert calls["n"] == 2  # json_schema attempt + prompt-based fallback
        assert len(caplog.records) == 1
        msg = caplog.records[0].getMessage()
        assert "grok-test" in msg  # model named
        assert "ValueError" in msg  # triggering exception class
        assert "response_format not supported" in msg  # exception message

    def test_transient_error_propagates_without_fallback(self, monkeypatch, caplog):
        provider = XAITextProvider(api_key="k")
        _stub_client(provider, monkeypatch)

        def fake_create(client, **kwargs):
            raise TransientProviderError("rate limited")

        monkeypatch.setattr(xai_mod, "_create", fake_create)

        with caplog.at_level(logging.WARNING, logger="polyptych.providers.xai"):
            with pytest.raises(TransientProviderError, match="rate limited"):
                provider.generate_structured("q", _Reply, "grok-test")
        # Transient errors must NOT trigger the prompt-based fallback warning.
        assert caplog.records == []


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


class TestGeminiHelpers:
    def test_extract_result_populates_usage(self):
        provider = GeminiTextProvider()
        resp = _gemini_response(prompt_tokens=90, output_tokens=40, total_tokens=130)
        result = provider._extract_result(resp, "gemini-test", 2.0)
        assert result.provider == "gemini"
        assert result.prompt_token_count == 90
        assert result.candidates_token_count == 40
        assert result.total_token_count == 130

    def test_extract_result_captures_thinking_tokens(self):
        provider = GeminiTextProvider()
        resp = _gemini_response(thoughts=250)
        result = provider._extract_result(resp, "gemini-test", 0.5)
        assert result.thoughts_token_count == 250

    def test_extract_result_skips_metadata_when_missing(self):
        provider = GeminiTextProvider()
        resp = SimpleNamespace(usage_metadata=None)
        result = provider._extract_result(resp, "gemini-test", 0.1)
        assert result.prompt_token_count is None
