"""Provider abstraction (Section 28 of the project plan).

A provider performs ONE job: natural language -> raw contract dict.
All validation, comparison, and drift classification stay deterministic
and provider-independent.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised when a provider cannot produce usable output."""


class ExtractionProvider(ABC):
    name: str = "base"

    @abstractmethod
    def extract_raw(self, text: str) -> dict:
        """Return a raw (unvalidated) contract dict for the given text."""

    def extract_raw_with_feedback(self, text: str, errors: list[str]) -> dict:
        """Retry hook: called when the previous output failed validation."""
        return self.extract_raw(text)
