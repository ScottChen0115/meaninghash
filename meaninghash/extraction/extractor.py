"""SemanticExtractor: raw provider output -> validated SemanticContract."""
from __future__ import annotations

from pydantic import ValidationError

from meaninghash.extraction.rule_based import parse_text
from meaninghash.models import (
    CanonicalForm,
    ContractSource,
    Polarity,
    Priority,
    Requirement,
    RequirementKind,
    SemanticContract,
    Strength,
    next_requirement_id,
)
from meaninghash.providers.base import ExtractionProvider, ProviderError

_GROUP_TO_KIND = {
    "goals": RequirementKind.GOAL,
    "constraints": RequirementKind.CONSTRAINT,
    "permissions": RequirementKind.PERMISSION,
    "preferences": RequirementKind.PREFERENCE,
    "assumptions": RequirementKind.ASSUMPTION,
}

MAX_RETRIES = 2


class ExtractionError(Exception):
    pass


class SemanticExtractor:
    def __init__(self, provider: ExtractionProvider) -> None:
        self.provider = provider

    def extract(
        self,
        text: str,
        source_type: str = "document",
        source_id: str = "",
        path: str | None = None,
    ) -> SemanticContract:
        raw, errors = None, []
        for attempt in range(MAX_RETRIES + 1):
            try:
                raw = (
                    self.provider.extract_raw(text)
                    if attempt == 0
                    else self.provider.extract_raw_with_feedback(text, errors)
                )
                return self._build(raw, text, source_type, source_id, path)
            except (ValidationError, ValueError, ExtractionError, ProviderError) as exc:
                errors.append(str(exc))
        raise ExtractionError(
            f"provider {self.provider.name!r} failed after {MAX_RETRIES + 1} attempts: "
            + "; ".join(errors[-1:])
        )

    def _build(
        self,
        raw: dict,
        text: str,
        source_type: str,
        source_id: str,
        path: str | None,
    ) -> SemanticContract:
        if not isinstance(raw, dict):
            raise ExtractionError("provider output must be a JSON object")
        contract = SemanticContract(
            source=ContractSource(type=source_type, source_id=source_id, path=path)
        )
        ids: list[str] = []
        for group, kind in _GROUP_TO_KIND.items():
            items = raw.get(group, []) or []
            if not isinstance(items, list):
                raise ExtractionError(f"{group!r} must be a list")
            for item in items:
                if not isinstance(item, dict):
                    raise ExtractionError(f"{group!r} items must be objects")
                rid = item.get("id") or next_requirement_id(kind, ids)
                if rid in ids:
                    rid = next_requirement_id(kind, ids)
                ids.append(rid)
                canon_raw = item.get("canonical") or {}
                if not isinstance(canon_raw, dict):
                    raise ExtractionError("canonical must be an object")
                requirement = Requirement(
                    id=rid,
                    kind=kind,
                    text=str(item.get("text") or item.get("natural_language") or ""),
                    canonical=CanonicalForm(
                        subject=str(canon_raw.get("subject", "")),
                        relation=str(canon_raw.get("relation", "")),
                        object=str(canon_raw.get("object", "")),
                        polarity=Polarity(canon_raw.get("polarity", "state")),
                    ),
                    strength=Strength(item.get("strength", "soft")),
                    priority=Priority(item.get("priority", "medium")),
                    scope=[str(s) for s in item.get("scope", [])],
                    confidence=float(item.get("confidence", 0.8)),
                )
                contract.requirements.append(requirement)
        return contract  # empty contracts are valid (e.g. free-form prose)


def extract_rule_based(text: str) -> dict:
    """Direct access to the deterministic parser (used by MockProvider)."""
    return parse_text(text)
