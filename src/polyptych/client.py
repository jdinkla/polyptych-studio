"""Multi-provider text generation client with fallback chain."""

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from common.usage_log import default_usage_log as _default_usage_log
from common.usage_log import log_usage
from .providers import get_text_provider, list_text_providers
from .providers.base import (
    BaseTextProvider,
    ContentBlockedError,
    TextGenerationResult,
    TransientProviderError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Sentinel used to distinguish "caller passed nothing" from "caller passed None".
_UNSET: object = object()


class TextClient:
    """Client for text generation with multi-provider support and fallback chain.

    Mirrors the ImageClient pattern: primary provider + automatic fallback
    to other providers when content is blocked.
    """

    def __init__(
        self,
        provider: str = "gemini",
        fallback: list[str] | None = None,
        api_key: str | None = None,
        usage_log: Path | None | object = _UNSET,
        model_resolver: Callable[[str, str], str] | None = None,
        thinking_budget_resolver: Callable[[str, str], int | None] | None = None,
    ):
        """Initialize the text client.

        Args:
            provider: Primary provider name (gemini, openai, xai, anthropic).
            fallback: Fallback provider chain. None = auto (all other providers).
                      Empty list or ["none"] = disable fallback.
            api_key: Optional API key for the primary provider.
            usage_log: Path to a JSONL file for logging usage.  Pass ``None``
                to disable logging.  When omitted, :func:`_default_usage_log`
                is called at construction time to resolve the path from the
                ``POLYPTYCH_USAGE_LOG`` env var or
                ``~/.cache/polyptych/usage.jsonl``.
            model_resolver: Callback (task_name, provider_name) -> model_string.
                           Used to resolve the correct model when falling back.
            thinking_budget_resolver: Callback (task_name, provider_name) -> budget.
                                     Returns thinking budget or None.
        """
        self.provider_name = provider
        self._api_key = api_key
        self._providers: dict[str, BaseTextProvider] = {}
        self.usage_log: Path | None = (
            _default_usage_log() if usage_log is _UNSET else usage_log  # type: ignore[assignment]
        )
        self.model_resolver = model_resolver
        self.thinking_budget_resolver = thinking_budget_resolver

        # Resolve fallback chain
        if fallback is not None and fallback == ["none"]:
            self._fallback_chain: list[str] = []
        elif fallback is not None:
            self._fallback_chain = [f for f in fallback if f != provider]
        else:
            # Auto: all other providers
            self._fallback_chain = [p for p in list_text_providers() if p != provider]

    def _get_provider(self, name: str) -> BaseTextProvider:
        """Get or create a provider instance (lazy initialization)."""
        if name not in self._providers:
            key = self._api_key if name == self.provider_name else None
            self._providers[name] = get_text_provider(name, api_key=key)
        return self._providers[name]

    def _log_result(
        self,
        gen_result: TextGenerationResult,
        method: str,
        task: str | None,
    ) -> None:
        """Log a generation result to the usage JSONL file."""
        if self.usage_log is None:
            return
        entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": gen_result.provider,
            "model": gen_result.model,
            "method": method,
            "task": task,
            "duration_s": gen_result.duration_s,
        }
        if gen_result.prompt_token_count is not None:
            entry["prompt_token_count"] = gen_result.prompt_token_count
        if gen_result.candidates_token_count is not None:
            entry["candidates_token_count"] = gen_result.candidates_token_count
        if gen_result.total_token_count is not None:
            entry["total_token_count"] = gen_result.total_token_count
        if gen_result.thoughts_token_count is not None:
            entry["thoughts_token_count"] = gen_result.thoughts_token_count
        self.usage_log.parent.mkdir(parents=True, exist_ok=True)
        log_usage(self.usage_log, entry)

    def _log_blocked(
        self,
        provider_name: str,
        model: str,
        task: str | None,
        error: ContentBlockedError,
        prompt: str,
    ) -> None:
        """Log a blocked request for debugging."""
        if self.usage_log is None:
            return
        blocked_log = self.usage_log.parent / "blocked-requests.jsonl"
        blocked_log.parent.mkdir(parents=True, exist_ok=True)
        log_usage(
            blocked_log,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provider": provider_name,
                "model": model,
                "task": task,
                "block_reason": error.block_reason,
                "message": str(error),
                "prompt": prompt,
            },
        )

    def _resolve_thinking_budget(
        self,
        task: str | None,
        provider_name: str,
    ) -> int | None:
        """Resolve the thinking budget for a provider and task.

        Returns None if budget cannot be resolved or is not applicable.
        """
        if self.thinking_budget_resolver is None or task is None:
            return None
        return self.thinking_budget_resolver(task, provider_name)

    def _resolve_fallback_model(
        self,
        task: str | None,
        fallback_provider: str,
    ) -> str | None:
        """Resolve the model string for a fallback provider.

        Returns None if model cannot be resolved (provider will be skipped).
        """
        if self.model_resolver is None or task is None:
            return None
        try:
            return self.model_resolver(task, fallback_provider)
        except KeyError:
            return None

    def _try_with_fallback(
        self,
        call: Callable[
            [BaseTextProvider, str, int | None], tuple[object, TextGenerationResult]
        ],
        method: str,
        model: str,
        prompt: str,
        task: str | None,
    ) -> object:
        """Run ``call`` against the primary provider, then each fallback provider.

        Fallback engages on two error classes:
        - ``ContentBlockedError``: the provider refused on content-policy grounds.
        - ``TransientProviderError``: the provider exhausted its own backoff retries
          (rate limits, timeouts, 5xx). Decision (P1.1): a persistently rate-limited
          provider should not kill a run when a fallback exists, so an exhausted
          transient failure is treated the same as a content block here.

        ``call(provider, model, thinking_budget)`` must return ``(value, gen_result)``;
        its returned ``value`` is what this method returns on the first successful call.
        """
        provider = self._get_provider(self.provider_name)
        thinking_budget = self._resolve_thinking_budget(task, self.provider_name)
        try:
            value, gen_result = call(provider, model, thinking_budget)
            self._log_result(gen_result, method, task)
            return value
        except ContentBlockedError as primary_err:
            self._log_blocked(self.provider_name, model, task, primary_err, prompt)
            logger.warning(
                "Content blocked by %s (%s), trying fallback providers",
                self.provider_name,
                model,
            )
            last_err: Exception = primary_err
        except TransientProviderError as primary_err:
            logger.warning(
                "Transient error from %s (%s) after retries, trying fallback: %s",
                self.provider_name,
                model,
                primary_err,
            )
            last_err = primary_err

        for fb_name in self._fallback_chain:
            fb_model = self._resolve_fallback_model(task, fb_name)
            if fb_model is None:
                logger.info(
                    "Skipping fallback %s: no model configured",
                    fb_name,
                )
                continue

            fb_budget = self._resolve_thinking_budget(task, fb_name)
            try:
                fb_provider = self._get_provider(fb_name)
                value, gen_result = call(fb_provider, fb_model, fb_budget)
                self._log_result(gen_result, method, task)
                logger.info(
                    "Fallback to %s (%s) succeeded",
                    fb_name,
                    fb_model,
                )
                return value
            except ContentBlockedError as fb_err:
                self._log_blocked(fb_name, fb_model, task, fb_err, prompt)
                logger.warning(
                    "Fallback %s (%s) also blocked",
                    fb_name,
                    fb_model,
                )
                last_err = fb_err
            except TransientProviderError as fb_err:
                logger.warning(
                    "Fallback %s (%s) transient error after retries: %s",
                    fb_name,
                    fb_model,
                    fb_err,
                )
                last_err = fb_err

        raise last_err

    def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        model: str,
        system_instruction: str | None = None,
        max_output_tokens: int | None = None,
        task: str | None = None,
    ) -> T:
        """Generate structured output using a Pydantic schema.

        Tries the primary provider first, then falls back to other providers
        on ContentBlockedError.

        Args:
            prompt: The prompt to send to the model.
            response_schema: Pydantic model class defining the expected output structure.
            model: Model to use for the primary provider.
            system_instruction: Optional system instruction for the model.
            max_output_tokens: Maximum number of tokens in the response.
            task: Optional task name for usage logging and model resolution.

        Returns:
            Validated Pydantic model instance with the generated content.
        """

        def call(provider: BaseTextProvider, m: str, budget: int | None):
            return provider.generate_structured(
                prompt,
                response_schema,
                m,
                system_instruction,
                max_output_tokens,
                budget,
            )

        return self._try_with_fallback(  # type: ignore[return-value]
            call,
            "generate_structured",
            model,
            prompt,
            task,
        )

    def generate_text(
        self,
        prompt: str,
        model: str,
        system_instruction: str | None = None,
        task: str | None = None,
    ) -> str:
        """Generate plain text output.

        Tries the primary provider first, then falls back to other providers
        on ContentBlockedError.

        Args:
            prompt: The prompt to send to the model.
            model: Model to use for the primary provider.
            system_instruction: Optional system instruction for the model.
            task: Optional task name for usage logging and model resolution.

        Returns:
            Generated text response.
        """

        def call(provider: BaseTextProvider, m: str, budget: int | None):
            return provider.generate_text(prompt, m, system_instruction, budget)

        return self._try_with_fallback(  # type: ignore[return-value]
            call,
            "generate_text",
            model,
            prompt,
            task,
        )


# Backward compatibility alias
GeminiTextClient = TextClient
