"""xAI (Grok) text generation provider."""

import json
import logging
import time
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from .base import (
    BaseTextProvider,
    ContentBlockedError,
    TextGenerationResult,
    TransientProviderError,
    map_openai_sdk_transient,
    retry_on_transient,
)

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


def _create(client: OpenAI, **kwargs):
    """Call the chat completions endpoint, retrying transient SDK errors."""

    def attempt():
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as err:
            transient = map_openai_sdk_transient(err)
            if transient is not None:
                raise transient from err
            raise

    return retry_on_transient(attempt)


class XAITextProvider(BaseTextProvider):
    """Text generation provider using xAI's Grok API.

    Uses the OpenAI SDK with a custom base URL.
    """

    ENV_KEYS = ["XAI_API_KEY"]
    BASE_URL = "https://api.x.ai/v1"

    def __init__(self, api_key: str | None = None):
        super().__init__(api_key)
        self._client: OpenAI | None = None

    @property
    def name(self) -> str:
        return "xai"

    def _get_client(self) -> OpenAI:
        if self._client is None:
            api_key = self._get_api_key(self.ENV_KEYS)
            self._client = OpenAI(api_key=api_key, base_url=self.BASE_URL)
        return self._client

    @staticmethod
    def _extract_result(
        response,
        model: str,
        duration_s: float,
    ) -> TextGenerationResult:
        result = TextGenerationResult(
            provider="xai",
            model=model,
            duration_s=round(duration_s, 3),
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            result.prompt_token_count = getattr(usage, "prompt_tokens", None)
            result.candidates_token_count = getattr(usage, "completion_tokens", None)
            result.total_token_count = getattr(usage, "total_tokens", None)
        return result

    @staticmethod
    def _check_content_blocked(response, model: str) -> None:
        """Raise ContentBlockedError if the response was filtered."""
        choice = response.choices[0]
        if choice.finish_reason == "content_filter":
            raise ContentBlockedError(
                f"Content blocked by xAI content filter (model={model})",
                block_reason="content_filter",
            )
        message = choice.message
        if hasattr(message, "refusal") and message.refusal:
            raise ContentBlockedError(
                f"xAI refused request: {message.refusal} (model={model})",
                block_reason="refusal",
            )

    def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        model: str,
        system_instruction: str | None = None,
        max_output_tokens: int | None = None,
        thinking_budget: int | None = None,
    ) -> tuple[T, TextGenerationResult]:
        client = self._get_client()

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        # Build JSON schema for response_format
        schema = response_schema.model_json_schema()

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.__name__,
                    "schema": schema,
                    "strict": False,
                },
            },
        }
        if max_output_tokens:
            kwargs["max_tokens"] = max_output_tokens

        def produce_response():
            t0 = time.monotonic()
            try:
                response = _create(client, **kwargs)
            except TransientProviderError:
                # Transient errors are already retried inside _create; let them
                # propagate so the client fallback chain can engage.
                raise
            except Exception as err:
                # xAI may not support json_schema response_format — fall back to
                # prompt-based JSON instruction + Pydantic validation. This is a
                # quality regression (loses server-side schema enforcement), so
                # surface it instead of swallowing it silently.
                logger.warning(
                    "xAI json_schema structured output failed for model %r; "
                    "falling back to prompt-based JSON (%s: %s)",
                    model,
                    type(err).__name__,
                    err,
                )
                del kwargs["response_format"]
                # Append JSON instruction to the user message
                json_instruction = (
                    f"\n\nRespond ONLY with valid JSON matching this schema:\n"
                    f"```json\n{json.dumps(schema, indent=2)}\n```"
                )
                kwargs["messages"][-1]["content"] += json_instruction
                response = _create(client, **kwargs)
            return response, time.monotonic() - t0

        return self._generate_structured_with_retry(
            response_schema,
            produce_response=produce_response,
            extract_result=lambda r, d: self._extract_result(r, model, d),
            check_content_blocked=lambda r: self._check_content_blocked(r, model),
            extract_json_text=lambda r: r.choices[0].message.content,
        )

    def generate_text(
        self,
        prompt: str,
        model: str,
        system_instruction: str | None = None,
        thinking_budget: int | None = None,
    ) -> tuple[str, TextGenerationResult]:
        client = self._get_client()

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        t0 = time.monotonic()
        response = _create(client, model=model, messages=messages)
        duration_s = time.monotonic() - t0
        gen_result = self._extract_result(response, model, duration_s)

        self._check_content_blocked(response, model)

        text = response.choices[0].message.content
        if text is None:
            raise ValueError(f"xAI returned empty response (model={model})")
        return text, gen_result
