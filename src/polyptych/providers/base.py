"""Base classes for text generation providers."""

import json
import os
import random
import sys
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")

# Max retries when truncated output fails validation
_MAX_TRUNCATION_RETRIES = 1

# Transient-error retry policy: 3 attempts total with exponential backoff + jitter.
_MAX_TRANSIENT_ATTEMPTS = 3
_TRANSIENT_BASE_DELAY_S = 1.0
_TRANSIENT_MAX_DELAY_S = 30.0

# Module-level sleep reference so tests can patch it (no real sleeping).
_sleep = time.sleep


def repair_truncated_json(text: str) -> dict | None:
    """Attempt to repair JSON truncated by output token limits.

    Handles the common case where the model hit max_tokens mid-string,
    leaving an unclosed quote and missing closing braces/brackets.

    Returns parsed dict if repair succeeds, None otherwise.
    """
    # Fast path: already valid
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    if not text or not text.lstrip().startswith("{"):
        return None

    # Walk the text tracking string/nesting state
    in_string = False
    stack: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if in_string:
            if ch == "\\" and i + 1 < len(text):
                i += 2  # skip escaped char
                continue
            if ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch in "{[":
                stack.append(ch)
            elif ch == "}" and stack and stack[-1] == "{":
                stack.pop()
            elif ch == "]" and stack and stack[-1] == "[":
                stack.pop()
        i += 1

    if not in_string and not stack:
        return None  # looks complete, can't help

    # Close unclosed string
    repaired = text
    if in_string:
        repaired += '"'

    # Strip trailing comma (common after truncation)
    stripped = repaired.rstrip()
    if stripped.endswith(","):
        repaired = stripped[:-1]

    # Close all open structures
    for opener in reversed(stack):
        repaired += "}" if opener == "{" else "]"

    try:
        result = json.loads(repaired)
        print(
            "  WARN: Repaired truncated JSON output "
            f"(closed {len(stack)} bracket(s), unclosed_string={in_string})",
            file=sys.stderr,
        )
        return result
    except json.JSONDecodeError:
        return None


class ContentBlockedError(ValueError):
    """Raised when the LLM blocks the request due to content policy."""

    def __init__(self, message: str, block_reason: str | None = None):
        super().__init__(message)
        self.block_reason = block_reason


class TruncatedOutputError(ValueError):
    """Raised when truncation-repaired JSON fails schema validation (retryable)."""

    pass


class TransientProviderError(Exception):
    """Raised when a provider call fails for a transient reason.

    Covers rate limits (HTTP 429), request timeouts, connection resets, and
    server-side 5xx errors. Providers map their SDK-specific exceptions to this
    type so the retry helper and the client fallback chain can treat them
    uniformly. The originating SDK exception is preserved via ``__cause__``.
    """

    pass


def retry_on_transient(
    call: Callable[[], R],
    *,
    max_attempts: int = _MAX_TRANSIENT_ATTEMPTS,
    base_delay_s: float = _TRANSIENT_BASE_DELAY_S,
    max_delay_s: float = _TRANSIENT_MAX_DELAY_S,
) -> R:
    """Run ``call``, retrying on ``TransientProviderError`` with backoff + jitter.

    Sleeps via the module-level ``_sleep`` reference (patchable in tests). After
    ``max_attempts`` the last ``TransientProviderError`` is re-raised so the
    caller (e.g. the client fallback chain) can react.
    """
    last_err: TransientProviderError | None = None
    for attempt in range(max_attempts):
        try:
            return call()
        except TransientProviderError as err:
            last_err = err
            if attempt + 1 >= max_attempts:
                break
            # Exponential backoff with full jitter, capped.
            window = min(max_delay_s, base_delay_s * (2**attempt))
            delay = random.uniform(0, window)
            print(
                f"  WARN: transient provider error (attempt {attempt + 1}/"
                f"{max_attempts}), retrying in {delay:.2f}s: {last_err}",
                file=sys.stderr,
            )
            _sleep(delay)
    assert last_err is not None  # loop only exits via return or this error
    raise last_err


def map_openai_sdk_transient(err: Exception) -> TransientProviderError | None:
    """Map an ``openai`` SDK exception to ``TransientProviderError`` if transient.

    Shared by the OpenAI and xAI providers (both use the ``openai`` SDK).
    Returns ``None`` for non-transient exceptions so the caller can re-raise.
    """
    from openai import APIConnectionError, APITimeoutError, RateLimitError

    if isinstance(err, (RateLimitError, APITimeoutError, APIConnectionError)):
        return TransientProviderError(str(err))

    # 5xx server errors carry a numeric .status_code on APIStatusError.
    status = getattr(err, "status_code", None)
    if isinstance(status, int) and 500 <= status < 600:
        return TransientProviderError(str(err))
    return None


@dataclass
class TextGenerationResult:
    """Result metadata from a text generation request."""

    provider: str
    model: str
    duration_s: float
    prompt_token_count: int | None = None
    candidates_token_count: int | None = None
    total_token_count: int | None = None
    thoughts_token_count: int | None = None
    extra: dict = field(default_factory=dict)


class BaseTextProvider(ABC):
    """Abstract base class for text generation providers."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        ...

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        model: str,
        system_instruction: str | None = None,
        max_output_tokens: int | None = None,
        thinking_budget: int | None = None,
    ) -> tuple[T, TextGenerationResult]:
        """Generate structured output using a Pydantic schema.

        Returns:
            Tuple of (validated Pydantic model, generation metadata).
        """
        ...

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        model: str,
        system_instruction: str | None = None,
        thinking_budget: int | None = None,
    ) -> tuple[str, TextGenerationResult]:
        """Generate plain text output.

        Returns:
            Tuple of (generated text, generation metadata).
        """
        ...

    def _parse_and_validate(
        self,
        json_text: str | None,
        response_schema: type[T],
    ) -> T:
        """Parse JSON text, repair if truncated, validate against schema.

        Raises:
            TruncatedOutputError: if repaired truncated JSON fails validation (retryable).
            json.JSONDecodeError: if JSON is completely unparseable.
            pydantic.ValidationError: if complete (non-truncated) JSON fails validation.
        """
        was_repaired = False
        try:
            data = json.loads(json_text or "")
        except (json.JSONDecodeError, TypeError):
            data = repair_truncated_json(json_text or "")
            if data is None:
                dump_path = Path(f"debug-{response_schema.__name__}.json")
                dump_path.write_text(json_text or "", encoding="utf-8")
                print(
                    f"  ERROR: Failed to parse {response_schema.__name__} response. "
                    f"Raw JSON dumped to {dump_path}",
                    file=sys.stderr,
                )
                raise json.JSONDecodeError(
                    "Failed to parse or repair JSON", json_text or "", 0
                )
            was_repaired = True

        try:
            return response_schema.model_validate(data)
        except Exception:
            dump_path = Path(f"debug-{response_schema.__name__}.json")
            dump_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            if was_repaired:
                print(
                    f"  WARN: Truncated output failed {response_schema.__name__} validation",
                    file=sys.stderr,
                )
                raise TruncatedOutputError(
                    f"Truncation-repaired JSON failed {response_schema.__name__} validation"
                )
            print(
                f"  ERROR: Failed to validate {response_schema.__name__} response. "
                f"Raw JSON dumped to {dump_path}",
                file=sys.stderr,
            )
            raise

    def _generate_structured_with_retry(
        self,
        response_schema: type[T],
        produce_response: Callable[[], tuple[Any, float]],
        extract_result: Callable[[Any, float], TextGenerationResult],
        check_content_blocked: Callable[[Any], None],
        extract_json_text: Callable[[Any], str | None],
    ) -> tuple[T, TextGenerationResult]:
        """Run the shared structured-generation truncation retry loop.

        Shared by the OpenAI and xAI providers (both wrap the ``openai`` SDK
        chat-completions flow). The provider supplies four callables:

        - ``produce_response``: makes the (already transient-retried) SDK call
          and returns ``(raw response, duration_s)``. The xAI provider uses this
          hook to add its json_schema -> prompt-based JSON fallback.
        - ``extract_result``: builds the ``TextGenerationResult`` metadata from
          ``(response, duration_s)``.
        - ``check_content_blocked``: raises ``ContentBlockedError`` if filtered.
        - ``extract_json_text``: pulls the JSON payload string from the response.

        Retries up to ``_MAX_TRUNCATION_RETRIES`` times on
        ``TruncatedOutputError``. ``TransientProviderError`` is handled inside
        ``produce_response`` (via ``retry_on_transient``) and propagates so the
        client fallback chain can engage.
        """
        for attempt in range(_MAX_TRUNCATION_RETRIES + 1):
            response, duration_s = produce_response()
            gen_result = extract_result(response, duration_s)
            check_content_blocked(response)

            json_text = extract_json_text(response)
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

    def _get_api_key(self, env_keys: list[str]) -> str:
        """Get API key from stored value or environment variables."""
        if self._api_key:
            return self._api_key

        for key in env_keys:
            value = os.environ.get(key)
            if value:
                return value

        raise ValueError(
            f"API key required for {self.name}. "
            f"Set one of {env_keys} environment variables, "
            "or pass api_key parameter."
        )
