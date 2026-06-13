"""Shared fixtures for polyptych tests."""

from __future__ import annotations

import pytest

from polyptych.model_config import ModelConfig

from .mock_client import MockTextClient


@pytest.fixture
def mock_client() -> MockTextClient:
    """Fresh MockTextClient instance, shared across all polyptych pipeline tests."""
    return MockTextClient()


@pytest.fixture
def test_model_config() -> ModelConfig:
    """Minimal ModelConfig that resolves any task to 'test-model'.

    Includes dummy entries for both anime (a0) and slide (task1) pipelines
    so _write_manifest can compute models_used across pipelines.
    """
    return ModelConfig(
        providers={
            "gemini": {"fast": "test-model", "thinking": "test-model"},
        },
        tasks={"a0": "fast", "task1": "fast"},
        max_output_tokens={},
        thinking_budget={},
    )


@pytest.fixture
def source_text() -> str:
    """Minimal 5-paragraph fiction for pipeline testing."""
    return (
        "Author Name - Test Story\n\n"
        "The office was quiet. Alice sat behind her desk, staring at the rain.\n\n"
        "A knock at the door startled her. She rose slowly, adjusting her grey coat.\n\n"
        "The stranger entered without waiting. His silhouette filled the doorframe.\n\n"
        "Alice studied him carefully. Something about his eyes felt familiar.\n\n"
        "The clock on the wall struck midnight. Neither of them moved."
    )
