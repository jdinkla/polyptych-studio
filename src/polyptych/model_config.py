"""Per-task model selection via config YAML."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ModelConfig:
    """Maps provider tiers to model strings and pipeline steps to tiers."""

    providers: dict[str, dict[str, str]] = field(default_factory=dict)
    tasks: dict[str, str] = field(default_factory=dict)
    max_output_tokens: dict[str, int] = field(default_factory=dict)
    thinking_budget: dict[str, int] = field(default_factory=dict)


def load_model_config(override: str | None = None) -> ModelConfig:
    """Load model_config.yaml from the repository root.

    Walks up from this module's directory until it finds model_config.yaml,
    which lives at the top level of the repository.

    Args:
        override: If set (from --model or $POLYPTYCH_MODEL; deprecated alias
                  $SLIDE_GEN_MODEL), forces both tiers for all providers to
                  this value.

    Returns:
        ModelConfig with providers and tasks populated.
    """
    # Walk up from src/polyptych/ to find the repo root
    config_path = Path(__file__).resolve().parent
    while config_path != config_path.parent:
        candidate = config_path / "model_config.yaml"
        if candidate.exists():
            config_path = candidate
            break
        config_path = config_path.parent
    else:
        raise FileNotFoundError("model_config.yaml not found in any parent directory")
    with open(config_path) as f:
        raw = yaml.safe_load(f)

    config = ModelConfig(
        providers=raw.get("providers", {}),
        tasks=raw.get("tasks", {}),
        max_output_tokens=raw.get("max_output_tokens", {}),
        thinking_budget=raw.get("thinking_budget", {}),
    )

    if override:
        for provider in config.providers:
            for tier in config.providers[provider]:
                config.providers[provider][tier] = override

    return config


def resolve_model(config: ModelConfig, task_name: str, provider: str = "gemini") -> str:
    """Look up the concrete model string for a pipeline step.

    Resolution: tasks[task_name] -> tier -> providers[provider][tier] -> model string.
    Falls back to 'fast' tier if task_name is not in config.tasks.

    Args:
        config: The loaded ModelConfig.
        task_name: Pipeline step name (e.g. "task2", "a1", "enrichment").
        provider: LLM provider key (default "gemini").

    Returns:
        Model string suitable for API calls.

    Raises:
        KeyError: If the provider is not configured.
    """
    tier = config.tasks.get(task_name, "fast")
    provider_tiers = config.providers[provider]
    return provider_tiers.get(tier, provider_tiers["fast"])


def resolve_max_output_tokens(config: ModelConfig, task_name: str) -> int | None:
    """Look up the max output token limit for a pipeline step.

    Args:
        config: The loaded ModelConfig.
        task_name: Pipeline step name (e.g. "n0", "a1", "task7").

    Returns:
        Token limit if configured, None otherwise (use model default).
    """
    return config.max_output_tokens.get(task_name)


_DEFAULT_THINKING_BUDGET = 10240


@dataclass
class ImageModelConfig:
    """Maps image generation providers to model strings."""

    providers: dict[str, str] = field(default_factory=dict)


def load_image_model_config(override: str | None = None) -> ImageModelConfig:
    """Load image_model_config.yaml from the repository root.

    Walks up from this module's directory until it finds the config file.
    Returns an empty config if the file is not found (safe fallback to
    provider built-in defaults).

    Args:
        override: If set (from --image-model or $POLYPTYCH_IMAGE_MODEL;
                  deprecated alias $SLIDE_GEN_IMAGE_MODEL), forces all
                  providers to this value.

    Returns:
        ImageModelConfig with providers populated.
    """
    config_path = Path(__file__).resolve().parent
    while config_path != config_path.parent:
        candidate = config_path / "image_model_config.yaml"
        if candidate.exists():
            config_path = candidate
            break
        config_path = config_path.parent
    else:
        return ImageModelConfig()

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    config = ImageModelConfig(providers=raw.get("providers", {}))

    if override:
        for provider in config.providers:
            config.providers[provider] = override

    return config


def resolve_image_model(config: ImageModelConfig, provider: str) -> str | None:
    """Look up the image model string for a provider.

    Args:
        config: The loaded ImageModelConfig.
        provider: Image generation provider key (gemini, openai, xai, vertex).

    Returns:
        Model string if configured, None otherwise. As of pixbridge 0.2.0 there
        are no provider built-in defaults: a None here means the generation call
        will raise ``ValueError`` ("A model must be specified"). Every provider
        used by Polyptych must therefore have an entry in image_model_config.yaml
        (or be overridden via --image-model / $POLYPTYCH_IMAGE_MODEL).
    """
    return config.providers.get(provider)


def resolve_thinking_budget(
    config: ModelConfig,
    task_name: str,
    provider: str,
) -> int | None:
    """Look up the extended thinking budget for a pipeline step.

    Returns None if the provider doesn't support extended thinking (i.e. not
    anthropic) or if the task is on the fast tier (no thinking needed).

    Args:
        config: The loaded ModelConfig.
        task_name: Pipeline step name (e.g. "a2", "task6").
        provider: LLM provider key.

    Returns:
        Thinking budget in tokens, or None if not applicable.
    """
    if provider != "anthropic":
        return None
    tier = config.tasks.get(task_name, "fast")
    if tier == "fast":
        return None
    return config.thinking_budget.get(
        task_name,
        config.thinking_budget.get("default", _DEFAULT_THINKING_BUDGET),
    )
