"""Text generation providers registry."""

from typing import Literal

from .base import BaseTextProvider, ContentBlockedError, TextGenerationResult
from .gemini import GeminiTextProvider

TextProviderName = Literal["gemini", "openai", "xai", "anthropic", "vertex"]

# Provider registry — lazily populated to avoid import-time dependency on optional SDKs
_TEXT_PROVIDERS: dict[str, type[BaseTextProvider]] = {
    "gemini": GeminiTextProvider,
}


def _ensure_provider(name: str) -> None:
    """Import and register a provider if not already loaded."""
    if name in _TEXT_PROVIDERS:
        return
    if name == "openai":
        from .openai import OpenAITextProvider

        _TEXT_PROVIDERS["openai"] = OpenAITextProvider
    elif name == "xai":
        from .xai import XAITextProvider

        _TEXT_PROVIDERS["xai"] = XAITextProvider
    elif name == "anthropic":
        from .anthropic import AnthropicTextProvider

        _TEXT_PROVIDERS["anthropic"] = AnthropicTextProvider
    elif name == "vertex":
        from .vertex import VertexTextProvider

        _TEXT_PROVIDERS["vertex"] = VertexTextProvider
    else:
        raise ValueError(
            f"Unknown text provider '{name}'. "
            f"Available providers: {list_text_providers()}"
        )


def get_text_provider(name: str, api_key: str | None = None) -> BaseTextProvider:
    """Get a text provider instance by name."""
    _ensure_provider(name)
    provider_class = _TEXT_PROVIDERS[name]
    return provider_class(api_key=api_key)


def list_text_providers() -> list[str]:
    """List text providers eligible for the *automatic* fallback chain.

    Deliberately excludes ``vertex``: it authenticates via gcloud Application
    Default Credentials (and requires ``GOOGLE_CLOUD_PROJECT``), not a simple
    API key, so silently adding it to every auto-fallback chain would produce
    noisy auth failures for the majority of users who haven't set ADC up.

    Vertex is still fully usable when requested explicitly (as the primary
    ``--text-provider`` or in an explicit ``--text-fallback`` list); see
    :func:`list_all_text_providers` for the complete selectable set used to
    build CLI choices.
    """
    return ["gemini", "openai", "xai", "anthropic"]


def list_all_text_providers() -> list[str]:
    """List every selectable text provider, including ``vertex``.

    Use this for CLI ``choices`` and anywhere a user can *explicitly* pick a
    provider. The auto-fallback chain uses the narrower
    :func:`list_text_providers` instead (see its docstring for why vertex is
    excluded there).
    """
    return [*list_text_providers(), "vertex"]


__all__ = [
    "BaseTextProvider",
    "ContentBlockedError",
    "GeminiTextProvider",
    "TextGenerationResult",
    "TextProviderName",
    "get_text_provider",
    "list_all_text_providers",
    "list_text_providers",
]
