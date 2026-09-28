"""Runtime settings passed to provider construction."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Settings:
    """Provider configuration (Section 28 of the plan)."""

    model: str | None = None
    base_url: str | None = None
    api_key_env: str = "OPENAI_API_KEY"
    timeout: float = 120.0
