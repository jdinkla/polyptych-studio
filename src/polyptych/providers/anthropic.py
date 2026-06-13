"""Anthropic (Claude) text generation provider."""

import json
import sys
import time
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from .base import (
    BaseTextProvider,
    ContentBlockedError,
    TextGenerationResult,
    TransientProviderError,
    TruncatedOutputError,
    _MAX_TRUNCATION_RETRIES,
    retry_on_transient,
)

T = TypeVar("T", bound=BaseModel)

DEFAULT_MAX_TOKENS = 16384


def _create(client: anthropic.Anthropic, **kwargs):
    """Call the messages endpoint, retrying transient SDK errors."""

    def attempt():
        try:
            return client.messages.create(**kwargs)
        except (
            anthropic.RateLimitError,
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
        ) as err:
            raise TransientProviderError(str(err)) from err
        except anthropic.APIStatusError as err:
            if 500 <= err.status_code < 600:
                raise TransientProviderError(str(err)) from err
            raise

    return retry_on_transient(attempt)


class AnthropicTextProvider(BaseTextProvider):
    """Text generation provider using Anthropic's Claude API.

    Supports extended thinking via the thinking_budget parameter, which
    gives Claude a configurable token budget for internal reasoning
    before producing the final response.
    """

    ENV_KEYS = ["ANTHROPIC_API_KEY"]

    def __init__(self, api_key: str | None = None):
        super().__init__(api_key)
        self._client: anthropic.Anthropic | None = None

    @property
    def name(self) -> str:
        return "anthropic"

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            api_key = self._get_api_key(self.ENV_KEYS)
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    @staticmethod
    def _extract_result(
        response,
        model: str,
        duration_s: float,
    ) -> TextGenerationResult:
        result = TextGenerationResult(
            provider="anthropic",
            model=model,
            duration_s=round(duration_s, 3),
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            result.prompt_token_count = getattr(usage, "input_tokens", None)
            result.candidates_token_count = getattr(usage, "output_tokens", None)
            if result.prompt_token_count and result.candidates_token_count:
                result.total_token_count = (
                    result.prompt_token_count + result.candidates_token_count
                )
        return result

    @staticmethod
    def _check_content_blocked(response, model: str) -> None:
        """Raise ContentBlockedError if the response was refused."""
        if getattr(response, "stop_reason", None) == "refusal":
            raise ContentBlockedError(
                f"Content blocked by Anthropic (model={model})",
                block_reason="refusal",
            )

    @staticmethod
    def _extract_text(response) -> str:
        """Extract text content from response, skipping thinking blocks."""
        parts = []
        for block in response.content:
            if block.type == "text":
                parts.append(block.text)
        return "".join(parts)

    @staticmethod
    def _build_kwargs(
        model: str,
        messages: list[dict],
        system_instruction: str | None,
        max_output_tokens: int | None,
        thinking_budget: int | None,
    ) -> dict:
        """Build kwargs dict for messages.create()."""
        max_tokens = max_output_tokens or DEFAULT_MAX_TOKENS

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if system_instruction:
            kwargs["system"] = system_instruction
        if thinking_budget:
            # Ensure max_tokens accommodates thinking + output
            kwargs["max_tokens"] = max(max_tokens, thinking_budget + 1024)
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget,
            }
        return kwargs

    def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        model: str,
        system_instruction: str | None = None,
        max_output_tokens: int | None = None,
        thinking_budget: int | None = None,
    ) -> tuple[T, TextGenerationResult]:
        for attempt in range(_MAX_TRUNCATION_RETRIES + 1):
            client = self._get_client()

            # Append JSON schema instruction to prompt (same approach as xAI fallback)
            schema = response_schema.model_json_schema()
            json_instruction = (
                f"\n\nRespond ONLY with valid JSON matching this schema:\n"
                f"```json\n{json.dumps(schema, indent=2)}\n```"
            )

            messages = [{"role": "user", "content": prompt + json_instruction}]
            kwargs = self._build_kwargs(
                model,
                messages,
                system_instruction,
                max_output_tokens,
                thinking_budget,
            )

            t0 = time.monotonic()
            response = _create(client, **kwargs)
            duration_s = time.monotonic() - t0
            gen_result = self._extract_result(response, model, duration_s)

            self._check_content_blocked(response, model)

            json_text = self._extract_text(response)
            try:
                result = self._parse_and_validate(json_text, response_schema)
                return result, gen_result
            except TruncatedOutputError:
                if attempt < _MAX_TRUNCATION_RETRIES:
                    print(
                        "  Retrying generation after truncated output...",
                        file=sys.stderr,
                    )
                    continue
                raise
        raise RuntimeError(
            "unreachable: retry loop exhausted without returning or raising"
        )

    def generate_text(
        self,
        prompt: str,
        model: str,
        system_instruction: str | None = None,
        thinking_budget: int | None = None,
    ) -> tuple[str, TextGenerationResult]:
        client = self._get_client()

        messages = [{"role": "user", "content": prompt}]
        kwargs = self._build_kwargs(
            model,
            messages,
            system_instruction,
            None,
            thinking_budget,
        )

        t0 = time.monotonic()
        response = _create(client, **kwargs)
        duration_s = time.monotonic() - t0
        gen_result = self._extract_result(response, model, duration_s)

        self._check_content_blocked(response, model)

        text = self._extract_text(response)
        if not text:
            raise ValueError(f"Anthropic returned empty response (model={model})")
        return text, gen_result
