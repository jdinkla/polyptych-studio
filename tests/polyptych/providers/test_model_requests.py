"""Request contracts for upgraded defaults, with no paid API calls."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from polyptych.providers.anthropic import AnthropicTextProvider
from polyptych.providers.openai import OpenAITextProvider
from polyptych.providers.xai import XAITextProvider


class Reply(BaseModel):
    answer: str


@pytest.mark.parametrize("structured", [False, True])
@pytest.mark.parametrize("budget", [None, 0, 10240])
@pytest.mark.parametrize(
    "provider_type,model,fast_effort",
    [
        (OpenAITextProvider, "gpt-5.6-sol", "none"),
        (OpenAITextProvider, "gpt-6-astra", "low"),
        (OpenAITextProvider, "gpt-6-astra-2026-09-03", "low"),
        (OpenAITextProvider, "gpt-4.1", None),
        (XAITextProvider, "grok-4.6", "low"),
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
    "model", ["claude-sonnet-5", "claude-opus-5", "claude-opus-5-20260903"]
)
def test_claude_5_requests(model, budget, structured):
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
    assert kwargs["thinking"] == {"type": "adaptive" if budget else "disabled"}
    assert kwargs["output_config"] == {"effort": "high" if budget else "low"}
    # Adaptive effort must not silently increase the configured output cap.
    assert kwargs["max_tokens"] == (8000 if structured else 16384)
