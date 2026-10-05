"""Request contracts for upgraded defaults, with no paid API calls."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from polyptych.model_config import ModelConfig, resolve_thinking_budget
from polyptych.providers.anthropic import AnthropicTextProvider
from polyptych.providers.gemini import GeminiTextProvider
from polyptych.providers.openai import OpenAITextProvider
from polyptych.providers.vertex import VertexTextProvider
from polyptych.providers.xai import XAITextProvider


class Reply(BaseModel):
    answer: str


@pytest.mark.parametrize("provider_type", [GeminiTextProvider, VertexTextProvider])
@pytest.mark.parametrize("structured", [False, True])
@pytest.mark.parametrize("tier", ["fast", "thinking"])
@pytest.mark.parametrize("model", ["gemini-3.8-flash", "gemini-3.1-pro-preview"])
def test_gemini_tier_requests(provider_type, structured, tier, model, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    provider = provider_type(api_key="test-key")
    client = MagicMock()
    provider._client = client
    client.models.generate_content.return_value = SimpleNamespace(
        text='{"answer":"ok"}',
        usage_metadata=None,
    )
    budget = resolve_thinking_budget(
        ModelConfig(tasks={"task": tier}),
        "task",
        provider.name,
    )
    if structured:
        result, _ = provider.generate_structured(
            "hello",
            Reply,
            model,
            max_output_tokens=8000,
            thinking_budget=budget,
        )
        assert result.answer == "ok"
    else:
        result, _ = provider.generate_text("hello", model, thinking_budget=budget)
        assert result == '{"answer":"ok"}'
    config = client.models.generate_content.call_args.kwargs["config"]
    if model == "gemini-3.8-flash":
        assert config.thinking_config.thinking_level == (
            "HIGH" if tier == "thinking" else "LOW"
        )
        assert config.thinking_config.thinking_budget is None
    else:
        # Keep provider defaults for other Gemini models and model overrides.
        assert config.thinking_config is None
    if structured:
        assert config.max_output_tokens == 8000
        assert config.response_mime_type == "application/json"


@pytest.mark.parametrize("structured", [False, True])
@pytest.mark.parametrize("budget", [None, 0, 10240])
@pytest.mark.parametrize(
    "provider_type,model,fast_effort",
    [
        (OpenAITextProvider, "gpt-5.6-sol", "none"),
        (OpenAITextProvider, "gpt-5.6-terra", "none"),
        (OpenAITextProvider, "gpt-6-astra", "low"),
        (OpenAITextProvider, "gpt-6-astra-2026-09-03", "low"),
        (OpenAITextProvider, "gpt-4.1", None),
        (XAITextProvider, "grok-4.6", "low"),
        (XAITextProvider, "grok-4.7", "low"),
        (XAITextProvider, "grok-4.20-non-reasoning", None),
    ],
)
def test_chat_requests(provider_type, model, fast_effort, budget, structured):
    provider = provider_type(api_key="test-key")
    client = MagicMock()
    provider._client = client
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content='{"answer":"ok"}', refusal=None),
            )
        ],
        usage=None,
    )
    if structured:
        result, _ = provider.generate_structured(
            "hello",
            Reply,
            model,
            max_output_tokens=8000,
            thinking_budget=budget,
        )
        assert result.answer == "ok"
    else:
        result, _ = provider.generate_text("hello", model, thinking_budget=budget)
        assert result == '{"answer":"ok"}'
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == model
    if fast_effort is None:
        assert "reasoning_effort" not in kwargs
    else:
        assert kwargs["reasoning_effort"] == ("high" if budget else fast_effort)
    if structured:
        limit_key = (
            "max_completion_tokens"
            if provider_type is OpenAITextProvider
            else "max_tokens"
        )
        assert kwargs[limit_key] == 8000
        assert kwargs["response_format"]["type"] == "json_schema"
        if provider_type is OpenAITextProvider:
            assert "max_tokens" not in kwargs


@pytest.mark.parametrize("structured", [False, True])
@pytest.mark.parametrize("budget", [None, 0, 10240])
@pytest.mark.parametrize(
    "model,thinking_off",
    [
        ("claude-sonnet-5", {"type": "disabled"}),
        ("claude-opus-5", {"type": "disabled"}),
        ("claude-opus-5-20260903", {"type": "disabled"}),
        # Sonnet 5.5, Opus 5.5 and Fable 5.1 reject "disabled" with a 400.
        ("claude-sonnet-5-5", {"type": "between_tools"}),
        ("claude-opus-5-5", None),
        ("claude-fable-5-1", None),
    ],
)
def test_claude_5_requests(model, thinking_off, budget, structured):
    provider = AnthropicTextProvider(api_key="test-key")
    client = MagicMock()
    provider._client = client
    client.messages.create.return_value = SimpleNamespace(
        stop_reason="end_turn",
        usage=None,
        content=[
            SimpleNamespace(type="thinking"),
            SimpleNamespace(type="text", text='{"answer":"ok"}'),
        ],
    )
    if structured:
        result, _ = provider.generate_structured(
            "hello",
            Reply,
            model,
            max_output_tokens=8000,
            thinking_budget=budget,
        )
        assert result.answer == "ok"
    else:
        result, _ = provider.generate_text("hello", model, thinking_budget=budget)
        assert result == '{"answer":"ok"}'
    kwargs = client.messages.create.call_args.kwargs
    if budget:
        assert kwargs["thinking"] == {"type": "adaptive"}
    elif thinking_off is None:
        assert "thinking" not in kwargs
    else:
        assert kwargs["thinking"] == thinking_off
    assert kwargs["output_config"] == {"effort": "high" if budget else "low"}
    # Adaptive effort must not silently increase the configured output cap.
    assert kwargs["max_tokens"] == (8000 if structured else 16384)
