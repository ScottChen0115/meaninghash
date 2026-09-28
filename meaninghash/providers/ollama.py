"""Ollama provider: fully local extraction via its OpenAI-compatible API."""
from __future__ import annotations

from meaninghash.providers.openai_compatible import OpenAICompatibleProvider


class OllamaProvider(OpenAICompatibleProvider):
    name = "ollama"

    def __init__(
        self,
        model: str = "llama3.1",
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        super().__init__(
            model=model,
            base_url=base_url or "http://localhost:11434/v1",
            api_key="ollama",
            timeout=timeout,
        )
