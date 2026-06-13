"""Tests for polyptych.client.TextClient (multi-provider fallback chain)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

import common.compat as compat_module
from polyptych.client import TextClient, _default_usage_log
from polyptych.providers.base import (
    BaseTextProvider,
    ContentBlockedError,
    TextGenerationResult,
    TransientProviderError,
)


# ---------------------------------------------------------------------------
# Test fixtures: a controllable fake provider + a registry monkeypatch
# ---------------------------------------------------------------------------


class _Item(BaseModel):
    name: str


class FakeProvider(BaseTextProvider):
    """Provider whose responses can be scripted per-test."""

    def __init__(
        self,
        provider_name: str,
        *,
        structured_response: BaseModel | None = None,
        text_response: str | None = None,
        raise_blocked: ContentBlockedError | None = None,
        raise_transient: TransientProviderError | None = None,
        raise_other: Exception | None = None,
    ):
        super().__init__(api_key=None)
        self._provider_name = provider_name
        self._structured_response = structured_response
        self._text_response = text_response
        self._raise_blocked = raise_blocked
        self._raise_transient = raise_transient
        self._raise_other = raise_other
        self.calls: list[dict] = []

    @property
    def name(self) -> str:
        return self._provider_name

    def generate_structured(
        self,
        prompt,
        response_schema,
        model,
        system_instruction=None,
        max_output_tokens=None,
        thinking_budget=None,
    ):
        self.calls.append(
            {
                "method": "generate_structured",
                "prompt": prompt,
                "model": model,
                "system_instruction": system_instruction,
                "max_output_tokens": max_output_tokens,
                "thinking_budget": thinking_budget,
            }
        )
        if self._raise_blocked is not None:
            raise self._raise_blocked
        if self._raise_transient is not None:
            raise self._raise_transient
        if self._raise_other is not None:
            raise self._raise_other
        gen = TextGenerationResult(
            provider=self._provider_name,
            model=model,
            duration_s=0.01,
            prompt_token_count=10,
            candidates_token_count=20,
            total_token_count=30,
        )
        return self._structured_response, gen

    def generate_text(
        self,
        prompt,
        model,
        system_instruction=None,
        thinking_budget=None,
    ):
        self.calls.append(
            {
                "method": "generate_text",
                "prompt": prompt,
                "model": model,
                "system_instruction": system_instruction,
                "thinking_budget": thinking_budget,
            }
        )
        if self._raise_blocked is not None:
            raise self._raise_blocked
        if self._raise_transient is not None:
            raise self._raise_transient
        if self._raise_other is not None:
            raise self._raise_other
        gen = TextGenerationResult(
            provider=self._provider_name,
            model=model,
            duration_s=0.01,
        )
        return self._text_response, gen


@pytest.fixture
def patched_registry(monkeypatch):
    """Replace polyptych.client.get_text_provider with a per-test registry.

    The fixture returns a dict you can populate with FakeProvider instances,
    keyed by provider name. The patched factory returns the registered
    instance (by name); requesting an unregistered provider raises KeyError.
    """
    providers: dict[str, FakeProvider] = {}

    def fake_get(name: str, api_key: str | None = None) -> BaseTextProvider:
        if name not in providers:
            raise KeyError(f"Test did not register a FakeProvider for {name!r}")
        return providers[name]

    monkeypatch.setattr("polyptych.client.get_text_provider", fake_get)
    return providers


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


# ---------------------------------------------------------------------------
# __init__: fallback chain resolution
# ---------------------------------------------------------------------------


class TestFallbackChainResolution:
    def test_auto_chain_excludes_primary(self):
        client = TextClient(provider="gemini", usage_log=None)
        # Auto = list_text_providers() minus primary.
        assert "gemini" not in client._fallback_chain
        assert set(client._fallback_chain) == {"openai", "xai", "anthropic"}

    def test_explicit_chain_filters_primary(self):
        client = TextClient(
            provider="openai",
            fallback=["gemini", "openai", "anthropic"],
            usage_log=None,
        )
        # Primary is silently filtered out even if listed.
        assert client._fallback_chain == ["gemini", "anthropic"]

    def test_explicit_empty_disables_fallback(self):
        client = TextClient(provider="gemini", fallback=[], usage_log=None)
        assert client._fallback_chain == []

    def test_none_sentinel_disables_fallback(self):
        client = TextClient(
            provider="gemini",
            fallback=["none"],
            usage_log=None,
        )
        assert client._fallback_chain == []


# ---------------------------------------------------------------------------
# generate_structured: success and fallback
# ---------------------------------------------------------------------------


class TestGenerateStructuredHappyPath:
    def test_primary_success_no_fallback_called(
        self,
        patched_registry,
        tmp_path,
    ):
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            structured_response=_Item(name="ok"),
        )
        patched_registry["openai"] = FakeProvider(
            "openai",
            structured_response=_Item(name="should-not-fire"),
        )
        client = TextClient(
            provider="gemini",
            fallback=["openai"],
            usage_log=tmp_path / "usage.jsonl",
        )
        out = client.generate_structured(
            prompt="hello",
            response_schema=_Item,
            model="gemini-x",
            task="t1",
        )
        assert out == _Item(name="ok")
        assert len(patched_registry["gemini"].calls) == 1
        assert patched_registry["openai"].calls == []

    def test_success_logs_usage(self, patched_registry, tmp_path):
        log = tmp_path / "usage.jsonl"
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            structured_response=_Item(name="ok"),
        )
        client = TextClient(
            provider="gemini",
            fallback=[],
            usage_log=log,
        )
        client.generate_structured(
            prompt="hi",
            response_schema=_Item,
            model="gemini-x",
            task="t1",
        )
        entries = _read_jsonl(log)
        assert len(entries) == 1
        e = entries[0]
        assert e["provider"] == "gemini"
        assert e["model"] == "gemini-x"
        assert e["method"] == "generate_structured"
        assert e["task"] == "t1"
        assert e["prompt_token_count"] == 10

    def test_usage_log_none_disables_logging(self, patched_registry, tmp_path):
        # No log path = no file should appear.
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            structured_response=_Item(name="ok"),
        )
        client = TextClient(provider="gemini", fallback=[], usage_log=None)
        client.generate_structured(
            prompt="hi",
            response_schema=_Item,
            model="gemini-x",
            task="t1",
        )
        assert not (tmp_path / "usage.jsonl").exists()


class TestGenerateStructuredFallback:
    def test_blocked_primary_falls_back_to_next(
        self,
        patched_registry,
        tmp_path,
    ):
        log = tmp_path / "usage.jsonl"
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            raise_blocked=ContentBlockedError("blocked", block_reason="SAFETY"),
        )
        patched_registry["openai"] = FakeProvider(
            "openai",
            structured_response=_Item(name="from-openai"),
        )

        def resolver(task: str, provider: str) -> str:
            return f"{provider}-model-for-{task}"

        client = TextClient(
            provider="gemini",
            fallback=["openai"],
            usage_log=log,
            model_resolver=resolver,
        )
        out = client.generate_structured(
            prompt="x",
            response_schema=_Item,
            model="gemini-x",
            task="t1",
        )
        assert out == _Item(name="from-openai")
        # Fallback provider was called with resolver-derived model.
        assert patched_registry["openai"].calls[0]["model"] == "openai-model-for-t1"
        # Successful fallback usage recorded.
        success_entries = _read_jsonl(log)
        assert len(success_entries) == 1
        assert success_entries[0]["provider"] == "openai"
        # Blocked primary recorded to sibling jsonl.
        blocked = _read_jsonl(tmp_path / "blocked-requests.jsonl")
        assert len(blocked) == 1
        assert blocked[0]["provider"] == "gemini"
        assert blocked[0]["block_reason"] == "SAFETY"
        assert blocked[0]["prompt"] == "x"

    def test_fallback_skipped_when_no_model_resolved(
        self,
        patched_registry,
        tmp_path,
    ):
        # First fallback returns no model (resolver raises KeyError),
        # client should silently skip it and try the next.
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            raise_blocked=ContentBlockedError("blocked"),
        )
        patched_registry["openai"] = FakeProvider(
            "openai",
            structured_response=_Item(name="should-not-fire"),
        )
        patched_registry["anthropic"] = FakeProvider(
            "anthropic",
            structured_response=_Item(name="from-anthropic"),
        )

        def resolver(task: str, provider: str) -> str:
            if provider == "openai":
                raise KeyError("no model configured for openai")
            return f"{provider}-model"

        client = TextClient(
            provider="gemini",
            fallback=["openai", "anthropic"],
            usage_log=tmp_path / "usage.jsonl",
            model_resolver=resolver,
        )
        out = client.generate_structured(
            prompt="x",
            response_schema=_Item,
            model="gemini-x",
            task="t1",
        )
        assert out == _Item(name="from-anthropic")
        # OpenAI never called because no model could be resolved.
        assert patched_registry["openai"].calls == []
        assert len(patched_registry["anthropic"].calls) == 1

    def test_fallback_skipped_when_resolver_missing(
        self,
        patched_registry,
        tmp_path,
    ):
        # Without a model_resolver at all, fallbacks can't resolve and
        # are skipped — primary error propagates.
        primary_err = ContentBlockedError("blocked-by-primary")
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            raise_blocked=primary_err,
        )
        patched_registry["openai"] = FakeProvider(
            "openai",
            structured_response=_Item(name="x"),
        )
        client = TextClient(
            provider="gemini",
            fallback=["openai"],
            usage_log=tmp_path / "usage.jsonl",
            # no model_resolver
        )
        with pytest.raises(ContentBlockedError) as exc:
            client.generate_structured(
                prompt="x",
                response_schema=_Item,
                model="gemini-x",
                task="t1",
            )
        # The last error raised is the primary's (fallback was skipped).
        assert exc.value is primary_err
        assert patched_registry["openai"].calls == []

    def test_all_blocked_raises_last_error(
        self,
        patched_registry,
        tmp_path,
    ):
        last_err = ContentBlockedError("blocked-by-openai")
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            raise_blocked=ContentBlockedError("blocked-by-gemini"),
        )
        patched_registry["openai"] = FakeProvider("openai", raise_blocked=last_err)
        client = TextClient(
            provider="gemini",
            fallback=["openai"],
            usage_log=tmp_path / "usage.jsonl",
            model_resolver=lambda task, provider: f"{provider}-m",
        )
        with pytest.raises(ContentBlockedError) as exc:
            client.generate_structured(
                prompt="x",
                response_schema=_Item,
                model="gemini-x",
                task="t1",
            )
        assert exc.value is last_err
        # Both blocks recorded.
        blocked = _read_jsonl(tmp_path / "blocked-requests.jsonl")
        assert [b["provider"] for b in blocked] == ["gemini", "openai"]

    def test_non_blocked_error_is_not_caught(
        self,
        patched_registry,
        tmp_path,
    ):
        # Plain RuntimeError (e.g. SDK error) should bubble up without
        # triggering fallback.
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            raise_other=RuntimeError("network down"),
        )
        patched_registry["openai"] = FakeProvider(
            "openai",
            structured_response=_Item(name="never"),
        )
        client = TextClient(
            provider="gemini",
            fallback=["openai"],
            usage_log=tmp_path / "usage.jsonl",
            model_resolver=lambda task, provider: f"{provider}-m",
        )
        with pytest.raises(RuntimeError, match="network down"):
            client.generate_structured(
                prompt="x",
                response_schema=_Item,
                model="gemini-x",
                task="t1",
            )
        assert patched_registry["openai"].calls == []


class TestTransientFallback:
    """Decision P1.1: an exhausted TransientProviderError engages the fallback chain."""

    def test_transient_primary_falls_back_to_next(self, patched_registry, tmp_path):
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            raise_transient=TransientProviderError("429 rate limited"),
        )
        patched_registry["openai"] = FakeProvider(
            "openai",
            structured_response=_Item(name="from-openai"),
        )
        client = TextClient(
            provider="gemini",
            fallback=["openai"],
            usage_log=tmp_path / "usage.jsonl",
            model_resolver=lambda task, provider: f"{provider}-m",
        )
        out = client.generate_structured(
            prompt="x",
            response_schema=_Item,
            model="gemini-x",
            task="t1",
        )
        assert out == _Item(name="from-openai")
        assert len(patched_registry["openai"].calls) == 1
        # Transient errors are not logged to blocked-requests.jsonl.
        assert not (tmp_path / "blocked-requests.jsonl").exists()

    def test_transient_exhausted_no_fallback_raises(self, patched_registry, tmp_path):
        # No fallback configured → the exhausted transient error surfaces.
        err = TransientProviderError("persistent 429")
        patched_registry["gemini"] = FakeProvider("gemini", raise_transient=err)
        client = TextClient(
            provider="gemini",
            fallback=[],
            usage_log=tmp_path / "usage.jsonl",
        )
        with pytest.raises(TransientProviderError) as exc:
            client.generate_structured(
                prompt="x",
                response_schema=_Item,
                model="gemini-x",
                task="t1",
            )
        assert exc.value is err

    def test_all_transient_raises_last(self, patched_registry, tmp_path):
        last = TransientProviderError("openai transient")
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            raise_transient=TransientProviderError("gemini transient"),
        )
        patched_registry["openai"] = FakeProvider("openai", raise_transient=last)
        client = TextClient(
            provider="gemini",
            fallback=["openai"],
            usage_log=tmp_path / "usage.jsonl",
            model_resolver=lambda task, provider: f"{provider}-m",
        )
        with pytest.raises(TransientProviderError) as exc:
            client.generate_structured(
                prompt="x",
                response_schema=_Item,
                model="gemini-x",
                task="t1",
            )
        assert exc.value is last

    def test_transient_then_blocked_fallback_mixed(self, patched_registry, tmp_path):
        # Primary exhausts transient retries; the single fallback is content-blocked.
        # The last error wins (the block).
        block = ContentBlockedError("openai blocked", block_reason="SAFETY")
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            raise_transient=TransientProviderError("gemini transient"),
        )
        patched_registry["openai"] = FakeProvider("openai", raise_blocked=block)
        client = TextClient(
            provider="gemini",
            fallback=["openai"],
            usage_log=tmp_path / "usage.jsonl",
            model_resolver=lambda task, provider: f"{provider}-m",
        )
        with pytest.raises(ContentBlockedError) as exc:
            client.generate_structured(
                prompt="x",
                response_schema=_Item,
                model="gemini-x",
                task="t1",
            )
        assert exc.value is block

    def test_transient_text_falls_back(self, patched_registry, tmp_path):
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            raise_transient=TransientProviderError("timeout"),
        )
        patched_registry["openai"] = FakeProvider("openai", text_response="rescued")
        client = TextClient(
            provider="gemini",
            fallback=["openai"],
            usage_log=tmp_path / "usage.jsonl",
            model_resolver=lambda task, provider: f"{provider}-m",
        )
        assert client.generate_text(prompt="p", model="gemini-x", task="t") == "rescued"


# ---------------------------------------------------------------------------
# generate_text: success and fallback (parity with generate_structured)
# ---------------------------------------------------------------------------


class TestGenerateText:
    def test_primary_success(self, patched_registry, tmp_path):
        patched_registry["gemini"] = FakeProvider("gemini", text_response="hello")
        client = TextClient(
            provider="gemini",
            fallback=[],
            usage_log=tmp_path / "usage.jsonl",
        )
        assert (
            client.generate_text(
                prompt="p",
                model="gemini-x",
                task="t",
            )
            == "hello"
        )

    def test_blocked_primary_falls_back(self, patched_registry, tmp_path):
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            raise_blocked=ContentBlockedError("nope"),
        )
        patched_registry["openai"] = FakeProvider("openai", text_response="rescued")
        client = TextClient(
            provider="gemini",
            fallback=["openai"],
            usage_log=tmp_path / "usage.jsonl",
            model_resolver=lambda task, provider: f"{provider}-m",
        )
        assert (
            client.generate_text(
                prompt="p",
                model="gemini-x",
                task="t",
            )
            == "rescued"
        )

    def test_all_blocked_raises_last(self, patched_registry, tmp_path):
        last = ContentBlockedError("openai blocked")
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            raise_blocked=ContentBlockedError("gemini blocked"),
        )
        patched_registry["openai"] = FakeProvider("openai", raise_blocked=last)
        client = TextClient(
            provider="gemini",
            fallback=["openai"],
            usage_log=tmp_path / "usage.jsonl",
            model_resolver=lambda task, provider: f"{provider}-m",
        )
        with pytest.raises(ContentBlockedError) as exc:
            client.generate_text(prompt="p", model="gemini-x", task="t")
        assert exc.value is last


# ---------------------------------------------------------------------------
# Resolvers: thinking_budget wiring
# ---------------------------------------------------------------------------


class TestResolverWiring:
    def test_thinking_budget_resolver_passed_to_primary(
        self,
        patched_registry,
        tmp_path,
    ):
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            structured_response=_Item(name="ok"),
        )
        seen: list[tuple[str, str]] = []

        def budget_resolver(task: str, provider: str) -> int | None:
            seen.append((task, provider))
            return 1234

        client = TextClient(
            provider="gemini",
            fallback=[],
            usage_log=tmp_path / "usage.jsonl",
            thinking_budget_resolver=budget_resolver,
        )
        client.generate_structured(
            prompt="p",
            response_schema=_Item,
            model="gemini-x",
            task="t1",
        )
        assert seen == [("t1", "gemini")]
        assert patched_registry["gemini"].calls[0]["thinking_budget"] == 1234

    def test_no_resolver_means_no_budget(self, patched_registry, tmp_path):
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            structured_response=_Item(name="ok"),
        )
        client = TextClient(
            provider="gemini",
            fallback=[],
            usage_log=tmp_path / "usage.jsonl",
        )
        client.generate_structured(
            prompt="p",
            response_schema=_Item,
            model="gemini-x",
            task="t1",
        )
        assert patched_registry["gemini"].calls[0]["thinking_budget"] is None

    def test_no_task_skips_resolver(self, patched_registry, tmp_path):
        # When task is None, resolver should not be called.
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            structured_response=_Item(name="ok"),
        )
        called = []

        def budget_resolver(task, provider):
            called.append((task, provider))
            return 999

        client = TextClient(
            provider="gemini",
            fallback=[],
            usage_log=tmp_path / "usage.jsonl",
            thinking_budget_resolver=budget_resolver,
        )
        client.generate_structured(
            prompt="p",
            response_schema=_Item,
            model="gemini-x",
            task=None,
        )
        assert called == []
        assert patched_registry["gemini"].calls[0]["thinking_budget"] is None


# ---------------------------------------------------------------------------
# Provider caching
# ---------------------------------------------------------------------------


class TestProviderCaching:
    def test_provider_instance_reused_across_calls(
        self,
        patched_registry,
        tmp_path,
    ):
        # _get_provider memoizes per-name; same instance should serve all calls.
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            structured_response=_Item(name="ok"),
        )
        client = TextClient(
            provider="gemini",
            fallback=[],
            usage_log=tmp_path / "usage.jsonl",
        )
        client.generate_structured(
            prompt="p",
            response_schema=_Item,
            model="gemini-x",
            task="t",
        )
        # Re-register a *different* response — but since the provider is
        # cached, it should still come from the original instance.
        original = patched_registry["gemini"]
        patched_registry["gemini"] = FakeProvider(
            "gemini",
            structured_response=_Item(name="different"),
        )
        out = client.generate_structured(
            prompt="p",
            response_schema=_Item,
            model="gemini-x",
            task="t",
        )
        assert out == _Item(name="ok")
        assert len(original.calls) == 2


# ---------------------------------------------------------------------------
# _default_usage_log: stable default path and env-var override
# ---------------------------------------------------------------------------


class TestDefaultUsageLog:
    """Unit tests for the _default_usage_log() helper and TextClient default."""

    def test_stable_dir_default(self, monkeypatch, tmp_path):
        """When no env var is set, default resolves to ~/.cache/polyptych/usage.jsonl."""
        monkeypatch.delenv("POLYPTYCH_USAGE_LOG", raising=False)
        monkeypatch.delenv("SLIDE_GEN_USAGE_LOG", raising=False)
        monkeypatch.setattr(
            compat_module.Path, "home", classmethod(lambda cls: tmp_path)
        )
        result = _default_usage_log()
        assert result == tmp_path / ".cache" / "polyptych" / "usage.jsonl"

    def test_polyptych_env_var_overrides(self, monkeypatch, tmp_path):
        """POLYPTYCH_USAGE_LOG overrides the stable default."""
        custom = tmp_path / "custom" / "my-usage.jsonl"
        monkeypatch.setenv("POLYPTYCH_USAGE_LOG", str(custom))
        monkeypatch.delenv("SLIDE_GEN_USAGE_LOG", raising=False)
        result = _default_usage_log()
        assert result == custom

    def test_slide_gen_env_var_fallback(self, monkeypatch, tmp_path):
        """SLIDE_GEN_USAGE_LOG is honoured as a deprecated fallback."""
        custom = tmp_path / "legacy-usage.jsonl"
        monkeypatch.delenv("POLYPTYCH_USAGE_LOG", raising=False)
        monkeypatch.setenv("SLIDE_GEN_USAGE_LOG", str(custom))
        result = _default_usage_log()
        assert result == custom

    def test_polyptych_takes_precedence_over_slide_gen(self, monkeypatch, tmp_path):
        """When both env vars are set, POLYPTYCH_USAGE_LOG wins."""
        monkeypatch.setenv("POLYPTYCH_USAGE_LOG", str(tmp_path / "new.jsonl"))
        monkeypatch.setenv("SLIDE_GEN_USAGE_LOG", str(tmp_path / "old.jsonl"))
        result = _default_usage_log()
        assert result == tmp_path / "new.jsonl"

    def test_client_default_resolves_via_helper(self, monkeypatch, tmp_path):
        """TextClient() with no usage_log kwarg uses _default_usage_log() at construction."""
        monkeypatch.delenv("POLYPTYCH_USAGE_LOG", raising=False)
        monkeypatch.delenv("SLIDE_GEN_USAGE_LOG", raising=False)
        monkeypatch.setattr(
            compat_module.Path, "home", classmethod(lambda cls: tmp_path)
        )
        client = TextClient(provider="gemini", fallback=[])
        assert client.usage_log == tmp_path / ".cache" / "polyptych" / "usage.jsonl"

    def test_client_explicit_none_disables_logging(self):
        """Passing usage_log=None still disables logging (unchanged behaviour)."""
        client = TextClient(provider="gemini", fallback=[], usage_log=None)
        assert client.usage_log is None

    def test_client_explicit_path_respected(self, tmp_path):
        """Passing an explicit path is used verbatim, not overridden."""
        explicit = tmp_path / "explicit.jsonl"
        client = TextClient(provider="gemini", fallback=[], usage_log=explicit)
        assert client.usage_log == explicit


# ---------------------------------------------------------------------------
# blocked-requests mkdir: parent dir is created before writing
# ---------------------------------------------------------------------------


class TestBlockedRequestsMkdir:
    """Ensure the parent dir of blocked-requests.jsonl is created if absent."""

    def test_blocked_log_parent_dir_created(self, patched_registry, tmp_path):
        """When usage_log is in a non-existent dir, _log_blocked creates it."""
        # Point usage_log at a path whose parent doesn't exist yet.
        nested_log = tmp_path / "deep" / "nested" / "usage.jsonl"
        assert not nested_log.parent.exists()

        patched_registry["gemini"] = FakeProvider(
            "gemini",
            raise_blocked=ContentBlockedError("blocked", block_reason="SAFETY"),
        )
        patched_registry["openai"] = FakeProvider(
            "openai",
            structured_response=_Item(name="ok"),
        )
        client = TextClient(
            provider="gemini",
            fallback=["openai"],
            usage_log=nested_log,
            model_resolver=lambda task, provider: f"{provider}-m",
        )
        client.generate_structured(
            prompt="x",
            response_schema=_Item,
            model="gemini-x",
            task="t1",
        )
        # The blocked-requests.jsonl should exist (its parent was mkdir'd).
        blocked = nested_log.parent / "blocked-requests.jsonl"
        assert blocked.exists()
        entries = [
            json.loads(line) for line in blocked.read_text().splitlines() if line
        ]
        assert len(entries) == 1
        assert entries[0]["block_reason"] == "SAFETY"

    def test_usage_log_parent_dir_created_on_write(self, patched_registry, tmp_path):
        """_log_result creates the usage_log parent dir if absent."""
        nested_log = tmp_path / "new-dir" / "usage.jsonl"
        assert not nested_log.parent.exists()

        patched_registry["gemini"] = FakeProvider(
            "gemini",
            structured_response=_Item(name="ok"),
        )
        client = TextClient(
            provider="gemini",
            fallback=[],
            usage_log=nested_log,
        )
        client.generate_structured(
            prompt="p",
            response_schema=_Item,
            model="gemini-x",
            task="t",
        )
        assert nested_log.exists()
