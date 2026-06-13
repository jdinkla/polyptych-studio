"""Tests for polyptych.model_config."""

import pytest

from polyptych.model_config import (
    ModelConfig,
    load_model_config,
    resolve_max_output_tokens,
    resolve_model,
)


@pytest.fixture
def sample_config() -> ModelConfig:
    return ModelConfig(
        providers={
            "gemini": {"fast": "gemini-fast-model", "thinking": "gemini-thinking-model"},
            "openai": {"fast": "gpt-4o-mini", "thinking": "gpt-4o"},
        },
        tasks={
            "task1": "fast",
            "task2": "thinking",
            "n1": "thinking",
        },
        max_output_tokens={
            "task7": 32000,
            "n1": 32000,
        },
    )


class TestLoadModelConfig:
    def test_loads_from_repo_root(self):
        config = load_model_config()
        assert config.providers
        assert config.tasks
        assert "gemini" in config.providers

    def test_override_replaces_all_tiers(self):
        config = load_model_config(override="custom-model")
        for provider_tiers in config.providers.values():
            for model in provider_tiers.values():
                assert model == "custom-model"


class TestResolveModel:
    def test_known_task_fast_tier(self, sample_config: ModelConfig):
        assert resolve_model(sample_config, "task1", "gemini") == "gemini-fast-model"

    def test_known_task_thinking_tier(self, sample_config: ModelConfig):
        assert resolve_model(sample_config, "task2", "gemini") == "gemini-thinking-model"

    def test_unknown_task_falls_back_to_fast(self, sample_config: ModelConfig):
        assert resolve_model(sample_config, "nonexistent", "gemini") == "gemini-fast-model"

    def test_different_provider(self, sample_config: ModelConfig):
        assert resolve_model(sample_config, "task2", "openai") == "gpt-4o"

    def test_unknown_provider_raises(self, sample_config: ModelConfig):
        with pytest.raises(KeyError):
            resolve_model(sample_config, "task1", "unknown_provider")

    def test_default_provider_is_gemini(self, sample_config: ModelConfig):
        assert resolve_model(sample_config, "task1") == "gemini-fast-model"


class TestResolveMaxOutputTokens:
    def test_configured_task_returns_limit(self, sample_config: ModelConfig):
        assert resolve_max_output_tokens(sample_config, "task7") == 32000

    def test_unconfigured_task_returns_none(self, sample_config: ModelConfig):
        assert resolve_max_output_tokens(sample_config, "task1") is None
