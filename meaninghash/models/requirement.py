"""Core requirement primitives for the Semantic Contract.

Every semantic element extracted from a document is a Requirement with:
- a kind (goal, constraint, permission, preference, assumption)
- a canonical form (subject / relation / object / polarity) used for
  deterministic comparison
- strength (hard = MUST, soft = SHOULD)
- priority, scope tags, and extraction confidence
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RequirementKind(str, Enum):
    GOAL = "goal"
    CONSTRAINT = "constraint"
    PERMISSION = "permission"
    PREFERENCE = "preference"
    ASSUMPTION = "assumption"


class Polarity(str, Enum):
    REQUIRE = "require"
    PROHIBIT = "prohibit"
    ALLOW = "allow"
    PREFER = "prefer"
    STATE = "state"


class Strength(str, Enum):
    HARD = "hard"
    SOFT = "soft"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CanonicalForm(BaseModel):
    """Deterministic meaning triple: (subject, relation, object) + polarity.

    Example:
        "Never delete the original photos."
        -> subject=original_photos, relation=delete, polarity=prohibit
    """

    subject: str = ""
    relation: str = ""
    object: str = ""
    polarity: Polarity = Polarity.STATE

    def triple(self) -> tuple[str, str, str]:
        return (self.subject, self.relation, self.object)


# Integrity-score weights (Section 20 of the project plan).
_KIND_WEIGHTS: dict[RequirementKind, int] = {
    RequirementKind.GOAL: 10,
    RequirementKind.CONSTRAINT: 8,
    RequirementKind.PERMISSION: 5,
    RequirementKind.ASSUMPTION: 4,
    RequirementKind.PREFERENCE: 2,
}


class Requirement(BaseModel):
    id: str
    kind: RequirementKind
    text: str
    canonical: CanonicalForm = Field(default_factory=CanonicalForm)
    strength: Strength = Strength.SOFT
    priority: Priority = Priority.MEDIUM
    scope: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @property
    def weight(self) -> int:
        """Weight of this requirement in the integrity score."""
        if self.priority == Priority.CRITICAL:
            return 10
        return _KIND_WEIGHTS.get(self.kind, 4)

    def brief(self) -> str:
        c = self.canonical
        return f"{c.subject}|{c.relation}|{c.object or '-'}|{c.polarity.value}"
