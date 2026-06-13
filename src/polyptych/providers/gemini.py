"""Gemini text generation provider."""

import sys
import time
from typing import TypeVar

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
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


def _generate_content(client: genai.Client, **kwargs):
    """Call generate_content, retrying transient SDK/transport errors."""

    def attempt():
        try:
            return client.models.generate_content(**kwargs)
        except genai_errors.ServerError as err:
            # All 5xx responses are transient.
            raise TransientProviderError(str(err)) from err
        except genai_errors.ClientError as err:
            # 429 (rate limit / quota) is the only retryable client error.
            if getattr(err, "code", None) == 429:
                raise TransientProviderError(str(err)) from err
            raise
        except (httpx.TimeoutException, httpx.TransportError) as err:
            # Connection resets, read timeouts, DNS failures, etc.
            raise TransientProviderError(str(err)) from err

    return retry_on_transient(attempt)


class GeminiTextProvider(BaseTextProvider):
    """Text generation provider using Google's Gemini API."""

    ENV_KEYS = ["GOOGLE_API_KEY", "GEMINI_API_KEY"]
    DEFAULT_TIMEOUT_MS = 300_000  # 5 minutes

    def __init__(self, api_key: str | None = None, timeout_ms: int | None = None):
        super().__init__(api_key)
        self._timeout_ms = timeout_ms or self.DEFAULT_TIMEOUT_MS
        self._client: genai.Client | None = None

    @property
    def name(self) -> str:
        return "gemini"

    def _get_client(self) -> genai.Client:
        if self._client is None:
            api_key = self._get_api_key(self.ENV_KEYS)
            self._client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=self._timeout_ms),
            )
        return self._client

    def _extract_result(
        self,
        response: types.GenerateContentResponse,
        model: str,
        duration_s: float,
    ) -> TextGenerationResult:
        result = TextGenerationResult(
            provider=self.name,
            model=model,
            duration_s=round(duration_s, 3),
        )
        meta = response.usage_metadata
        if meta is not None:
            result.prompt_token_count = meta.prompt_token_count
            result.candidates_token_count = meta.candidates_token_count
            result.total_token_count = meta.total_token_count
            if meta.thoughts_token_count:
                result.thoughts_token_count = meta.thoughts_token_count
        return result

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
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            )
            if system_instruction:
                config.system_instruction = system_instruction
            if max_output_tokens:
                config.max_output_tokens = max_output_tokens

            client = self._get_client()
            t0 = time.monotonic()
            response = _generate_content(
                client,
                model=model,
                contents=prompt,
                config=config,
            )
            duration_s = time.monotonic() - t0
            gen_result = self._extract_result(response, model, duration_s)

            json_text = response.text
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
        config = types.GenerateContentConfig()
        if system_instruction:
            config.system_instruction = system_instruction

        client = self._get_client()
        t0 = time.monotonic()
        response = _generate_content(
            client,
            model=model,
            contents=prompt,
            config=config,
        )
        duration_s = time.monotonic() - t0
        gen_result = self._extract_result(response, model, duration_s)

        if response.text is None:
            details = []
            block_reason = None
            if response.candidates:
                c = response.candidates[0]
                if c.finish_reason:
                    details.append(f"finish_reason={c.finish_reason}")
                if c.finish_message:
                    details.append(f"finish_message={c.finish_message}")
            if hasattr(response, "prompt_feedback") and response.prompt_feedback:
                pf = response.prompt_feedback
                if hasattr(pf, "block_reason") and pf.block_reason:
                    block_reason = str(pf.block_reason)
                    details.append(f"block_reason={block_reason}")
            detail_str = f" ({', '.join(details)})" if details else ""
            msg = f"LLM returned empty response{detail_str} (model={model})"
            if block_reason:
                raise ContentBlockedError(msg, block_reason=block_reason)
            raise ValueError(msg)

        return response.text, gen_result
