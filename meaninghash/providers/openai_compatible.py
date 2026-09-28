"""OpenAI-compatible chat-completions provider (OpenAI, LM Studio, vLLM...)."""
from __future__ import annotations

import json
import os
import re

import httpx

from meaninghash.extraction.prompts import (
    EXAMPLE_INPUT,
    EXAMPLE_OUTPUT,
    EXTRACTION_SYSTEM_PROMPT,
)
from meaninghash.providers.base import ExtractionProvider, ProviderError


def _parse_json(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("expected a JSON object", text, 0)
    return parsed


class OpenAICompatibleProvider(ExtractionProvider):
    name = "openai-compatible"

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        api_key: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self.api_key = api_key or os.environ.get(api_key_env)
        self.timeout = timeout
        if not self.api_key:
            raise ProviderError(
                f"missing API key: set ${api_key_env} or pass api_key="
            )

    def _chat(self, messages: list[dict]) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"request failed: {exc}") from exc
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise ProviderError(f"unexpected response shape: {exc}") from exc
        try:
            return _parse_json(content)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"model returned invalid JSON: {exc}") from exc

    def extract_raw(self, text: str) -> dict:
        system = (
            f"{EXTRACTION_SYSTEM_PROMPT}\n\nExample input:\n{EXAMPLE_INPUT}\n"
            f"Example output:\n{EXAMPLE_OUTPUT}"
        )
        return self._chat([
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ])

    def extract_raw_with_feedback(self, text: str, errors: list[str]) -> dict:
        system = f"{EXTRACTION_SYSTEM_PROMPT}"
        return self._chat([
            {"role": "system", "content": system},
            {"role": "user", "content": text},
            {"role": "assistant", "content": "{invalid}"},
            {
                "role": "user",
                "content": (
                    "Your previous output was invalid: "
                    + "; ".join(errors[-2:])
                    + " Return ONLY corrected valid JSON matching the schema."
                ),
            },
        ])
