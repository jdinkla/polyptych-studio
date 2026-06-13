"""Tests for polyptych.providers.base."""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, ValidationError

from polyptych.providers import base as base_mod
from polyptych.providers.base import (
    BaseTextProvider,
    ContentBlockedError,
    TextGenerationResult,
    TransientProviderError,
    TruncatedOutputError,
    map_openai_sdk_transient,
    repair_truncated_json,
    retry_on_transient,
)
from polyptych.providers import (
    get_text_provider,
    list_all_text_providers,
    list_text_providers,
)


# ---------------------------------------------------------------------------
# Fixture schemas
# ---------------------------------------------------------------------------


class _Item(BaseModel):
    name: str
    value: int


class _Container(BaseModel):
    items: list[_Item]
    title: str


# ---------------------------------------------------------------------------
# repair_truncated_json
# ---------------------------------------------------------------------------


class TestRepairTruncatedJson:
    def test_valid_json_passthrough(self):
        assert repair_truncated_json('{"a": 1}') == {"a": 1}

    def test_empty_string_returns_none(self):
        assert repair_truncated_json("") is None

    def test_non_object_start_returns_none(self):
        assert repair_truncated_json("[1, 2, 3") is None

    def test_complete_but_invalid_returns_none(self):
        # Looks complete (no open brackets, no open string) but isn't valid JSON.
        assert repair_truncated_json('{"a": notjson}') is None

    def test_unclosed_string_repaired(self, capsys):
        truncated = '{"name": "alice'
        result = repair_truncated_json(truncated)
        assert result == {"name": "alice"}
        # Should warn to stderr that it repaired
        assert "Repaired truncated JSON" in capsys.readouterr().err

    def test_missing_closing_brace_repaired(self):
        result = repair_truncated_json('{"a": 1, "b": 2')
        assert result == {"a": 1, "b": 2}

    def test_nested_unclosed_repaired(self):
        result = repair_truncated_json('{"outer": {"inner": "val')
        assert result == {"outer": {"inner": "val"}}

    def test_unclosed_array_repaired(self):
        result = repair_truncated_json('{"items": [1, 2, 3')
        assert result == {"items": [1, 2, 3]}

    def test_trailing_comma_stripped(self):
        result = repair_truncated_json('{"a": 1, "b": 2,')
        assert result == {"a": 1, "b": 2}

    def test_escaped_quote_inside_string(self):
        # Escape sequence shouldn't fool the string-state tracker.
        result = repair_truncated_json(r'{"msg": "she said \"hi')
        assert result == {"msg": 'she said "hi'}


# ---------------------------------------------------------------------------
# ContentBlockedError
# ---------------------------------------------------------------------------


class TestContentBlockedError:
    def test_is_value_error(self):
        err = ContentBlockedError("blocked")
        assert isinstance(err, ValueError)

    def test_block_reason_default_none(self):
        err = ContentBlockedError("blocked")
        assert err.block_reason is None

    def test_block_reason_preserved(self):
        err = ContentBlockedError("blocked", block_reason="SAFETY")
        assert err.block_reason == "SAFETY"
        assert str(err) == "blocked"


# ---------------------------------------------------------------------------
# TextGenerationResult
# ---------------------------------------------------------------------------


class TestTextGenerationResult:
    def test_required_fields_only(self):
        r = TextGenerationResult(provider="gemini", model="m", duration_s=1.5)
        assert r.provider == "gemini"
        assert r.model == "m"
        assert r.duration_s == 1.5
        assert r.prompt_token_count is None
        assert r.candidates_token_count is None
        assert r.total_token_count is None
        assert r.thoughts_token_count is None
        assert r.extra == {}

    def test_extra_is_independent_per_instance(self):
        a = TextGenerationResult(provider="p", model="m", duration_s=0.0)
        b = TextGenerationResult(provider="p", model="m", duration_s=0.0)
        a.extra["x"] = 1
        assert b.extra == {}


# ---------------------------------------------------------------------------
# BaseTextProvider._parse_and_validate
# ---------------------------------------------------------------------------


class _StubProvider(BaseTextProvider):
    """Concrete subclass that exposes only what we need to test base behavior."""

    @property
    def name(self) -> str:
        return "stub"

    def generate_structured(self, *args, **kwargs):  # pragma: no cover - not used
        raise NotImplementedError

    def generate_text(self, *args, **kwargs):  # pragma: no cover - not used
        raise NotImplementedError


class TestParseAndValidate:
    def test_valid_json_validates(self):
        provider = _StubProvider()
        out = provider._parse_and_validate(
            '{"name": "alice", "value": 7}',
            _Item,
        )
        assert out == _Item(name="alice", value=7)

    def test_truncated_json_repairs_then_validates(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        provider = _StubProvider()
        # Truncated mid-string — repair closes the string.
        out = provider._parse_and_validate(
            '{"name": "alice", "value": 7',
            _Item,
        )
        assert out == _Item(name="alice", value=7)

    def test_truncated_repair_invalid_raises_truncated_error(
        self,
        tmp_path,
        monkeypatch,
    ):
        monkeypatch.chdir(tmp_path)
        provider = _StubProvider()
        # Repair will close the string, but the schema requires `value: int`
        # which is missing — repaired dict fails validation.
        with pytest.raises(TruncatedOutputError):
            provider._parse_and_validate('{"name": "alice"', _Item)
        # Debug dump file is written to CWD with the schema name.
        assert (tmp_path / "debug-_Item.json").exists()

    def test_complete_invalid_raises_validation_error(
        self,
        tmp_path,
        monkeypatch,
    ):
        monkeypatch.chdir(tmp_path)
        provider = _StubProvider()
        # Valid JSON, but `value` is wrong type and not truncated.
        with pytest.raises(ValidationError):
            provider._parse_and_validate(
                '{"name": "alice", "value": "not-an-int"}',
                _Item,
            )

    def test_unparseable_garbage_raises_json_error(
        self,
        tmp_path,
        monkeypatch,
    ):
        monkeypatch.chdir(tmp_path)
        provider = _StubProvider()
        with pytest.raises(json.JSONDecodeError):
            provider._parse_and_validate("not json at all", _Item)
        # Raw text dumped to debug file for postmortem.
        assert (tmp_path / "debug-_Item.json").exists()

    def test_none_input_raises_json_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        provider = _StubProvider()
        with pytest.raises(json.JSONDecodeError):
            provider._parse_and_validate(None, _Item)


# ---------------------------------------------------------------------------
# BaseTextProvider._get_api_key
# ---------------------------------------------------------------------------


class TestGetApiKey:
    def test_constructor_key_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("STUB_KEY", "env-value")
        provider = _StubProvider(api_key="explicit-value")
        assert provider._get_api_key(["STUB_KEY"]) == "explicit-value"

    def test_falls_back_to_env_var(self, monkeypatch):
        monkeypatch.setenv("STUB_KEY", "env-value")
        provider = _StubProvider()
        assert provider._get_api_key(["STUB_KEY"]) == "env-value"

    def test_tries_env_keys_in_order(self, monkeypatch):
        monkeypatch.delenv("FIRST_KEY", raising=False)
        monkeypatch.setenv("SECOND_KEY", "second-value")
        provider = _StubProvider()
        assert provider._get_api_key(["FIRST_KEY", "SECOND_KEY"]) == "second-value"

    def test_empty_env_var_skipped(self, monkeypatch):
        monkeypatch.setenv("EMPTY_KEY", "")
        monkeypatch.setenv("REAL_KEY", "real-value")
        provider = _StubProvider()
        assert provider._get_api_key(["EMPTY_KEY", "REAL_KEY"]) == "real-value"

    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("MISSING_KEY", raising=False)
        provider = _StubProvider()
        with pytest.raises(ValueError, match="API key required for stub"):
            provider._get_api_key(["MISSING_KEY"])


# ---------------------------------------------------------------------------
# Provider registry (polyptych.providers.__init__)
# ---------------------------------------------------------------------------


class TestProviderRegistry:
    def test_list_text_providers_returns_expected_set(self):
        # The auto-fallback set: vertex is deliberately excluded because it
        # needs gcloud ADC auth, not a plain API key (see the docstring).
        assert list_text_providers() == ["gemini", "openai", "xai", "anthropic"]
        assert "vertex" not in list_text_providers()

    def test_list_all_text_providers_includes_vertex(self):
        # The complete selectable set (used for CLI choices) adds vertex.
        all_providers = list_all_text_providers()
        assert all_providers == ["gemini", "openai", "xai", "anthropic", "vertex"]
        # Auto-fallback set is a strict subset of the explicit-selection set.
        assert set(list_text_providers()).issubset(set(all_providers))

    def test_get_text_provider_gemini(self):
        provider = get_text_provider("gemini")
        assert isinstance(provider, BaseTextProvider)
        assert provider.name == "gemini"

    @pytest.mark.parametrize("name", ["openai", "xai", "anthropic"])
    def test_get_text_provider_lazy_imports(self, name):
        # These shouldn't fail at import-time even though their SDKs may have
        # heavy dependencies — the registry is documented as lazy.
        provider = get_text_provider(name)
        assert isinstance(provider, BaseTextProvider)

    def test_get_text_provider_vertex_requires_project(self, monkeypatch):
        # Vertex isn't in list_text_providers() (it's not used in the fallback
        # chain), and its constructor requires GOOGLE_CLOUD_PROJECT eagerly.
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        with pytest.raises(EnvironmentError, match="GOOGLE_CLOUD_PROJECT"):
            get_text_provider("vertex")

    def test_get_text_provider_vertex_succeeds_with_project(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
        provider = get_text_provider("vertex")
        assert isinstance(provider, BaseTextProvider)

    def test_get_text_provider_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown text provider"):
            get_text_provider("does-not-exist")


# ---------------------------------------------------------------------------
# retry_on_transient + map_openai_sdk_transient
# ---------------------------------------------------------------------------


@pytest.fixture
def no_sleep(monkeypatch):
    """Patch the module-level sleep so retries don't actually wait.

    Returns the list of sleep durations the helper requested.
    """
    durations: list[float] = []
    monkeypatch.setattr(base_mod, "_sleep", durations.append)
    return durations


class TestRetryOnTransient:
    def test_success_first_try_no_sleep(self, no_sleep):
        result = retry_on_transient(lambda: "ok")
        assert result == "ok"
        assert no_sleep == []

    def test_fails_twice_then_succeeds(self, no_sleep):
        attempts = {"n": 0}

        def call():
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise TransientProviderError(f"boom {attempts['n']}")
            return "recovered"

        result = retry_on_transient(call)
        assert result == "recovered"
        assert attempts["n"] == 3
        # Backoff slept between the two failures (2 sleeps for 3 attempts).
        assert len(no_sleep) == 2
        assert all(d >= 0 for d in no_sleep)

    def test_exhausts_and_reraises_last(self, no_sleep):
        attempts = {"n": 0}

        def call():
            attempts["n"] += 1
            raise TransientProviderError(f"persistent {attempts['n']}")

        with pytest.raises(TransientProviderError, match="persistent 3"):
            retry_on_transient(call)
        # Default 3 attempts → 2 sleeps before giving up.
        assert attempts["n"] == 3
        assert len(no_sleep) == 2

    def test_non_transient_not_retried(self, no_sleep):
        attempts = {"n": 0}

        def call():
            attempts["n"] += 1
            raise RuntimeError("not transient")

        with pytest.raises(RuntimeError, match="not transient"):
            retry_on_transient(call)
        assert attempts["n"] == 1
        assert no_sleep == []

    def test_backoff_is_bounded(self, no_sleep, monkeypatch):
        # With jitter forced to its max (random.uniform returns upper bound),
        # delays must respect the cap.
        monkeypatch.setattr(base_mod.random, "uniform", lambda lo, hi: hi)

        def call():
            raise TransientProviderError("x")

        with pytest.raises(TransientProviderError):
            retry_on_transient(call, max_attempts=5, base_delay_s=1.0, max_delay_s=4.0)
        assert all(d <= 4.0 for d in no_sleep)


class TestMapOpenAISdkTransient:
    def test_rate_limit_mapped(self):
        from openai import RateLimitError

        err = RateLimitError.__new__(RateLimitError)
        Exception.__init__(err, "429 rate limited")
        mapped = map_openai_sdk_transient(err)
        assert isinstance(mapped, TransientProviderError)

    def test_5xx_status_mapped(self):
        class FakeStatusErr(Exception):
            status_code = 503

        mapped = map_openai_sdk_transient(FakeStatusErr("server down"))
        assert isinstance(mapped, TransientProviderError)

    def test_4xx_status_not_mapped(self):
        class FakeStatusErr(Exception):
            status_code = 400

        assert map_openai_sdk_transient(FakeStatusErr("bad request")) is None

    def test_unrelated_not_mapped(self):
        assert map_openai_sdk_transient(ValueError("nope")) is None
