"""Provider factory."""
from __future__ import annotations

from meaninghash.providers.base import ExtractionProvider, ProviderError
from meaninghash.providers.mock import MockProvider
from meaninghash.providers.ollama import OllamaProvider
from meaninghash.providers.openai_compatible import OpenAICompatibleProvider

__all__ = [
    "ExtractionProvider",
    "ProviderError",
    "MockProvider",
    "OpenAICompatibleProvider",
    "OllamaProvider",
    "create_provider",
]


def create_provider(name: str, settings) -> ExtractionProvider:
    """Instantiate a provider by name using a Settings object."""
    name = (name or "mock").lower()
    if name == "mock":
        return MockProvider()
    if name in ("openai", "openai-compatible", "compatible"):
        return OpenAICompatibleProvider(
            model=settings.model,
            base_url=settings.base_url,
            api_key_env=settings.api_key_env,
        )
    if name == "ollama":
        return OllamaProvider(
            model=settings.model or "llama3.1",
            base_url=settings.base_url,
        )
    raise ValueError(
        f"unknown provider {name!r}; expected one of: "
        "mock, openai-compatible, ollama"
    )
