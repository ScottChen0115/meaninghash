"""Deterministic offline provider used by tests, CI, and the demo."""
from __future__ import annotations

from meaninghash.extraction.rule_based import parse_text
from meaninghash.providers.base import ExtractionProvider


class MockProvider(ExtractionProvider):
    """Dictionary-driven extractor: no network, no keys, fully reproducible.

    Quality is intentionally lower than an LLM provider; its purpose is a
    stable baseline for the deterministic comparison pipeline.
    """

    name = "mock"

    def extract_raw(self, text: str) -> dict:
        return parse_text(text)
