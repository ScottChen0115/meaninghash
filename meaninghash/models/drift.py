"""Drift taxonomy, severity levels, and report models."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DriftType(str, Enum):
    NO_DRIFT = "no_drift"
    REQUIREMENT_DROPPED = "requirement_dropped"
    CONSTRAINT_REVERSAL = "constraint_reversal"
    CONSTRAINT_WEAKENED = "constraint_weakened"
    CONSTRAINT_STRENGTHENED = "constraint_strengthened"
    SCOPE_NARROWED = "scope_narrowed"
    SCOPE_EXPANDED = "scope_expanded"
    GOAL_CHANGED = "goal_changed"
    UNSUPPORTED_ADDITION = "unsupported_addition"
    INTERNAL_CONFLICT = "internal_conflict"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return {Severity.INFO: 0, Severity.LOW: 1, Severity.MEDIUM: 2,
                Severity.HIGH: 3, Severity.CRITICAL: 4}[self]

    @classmethod
    def at_least(cls, level: "Severity | str") -> list["Severity"]:
        threshold = cls(level) if isinstance(level, str) else level
        return [s for s in cls if s.rank >= threshold.rank]


# Exit codes (Section 24 of the plan):
#   0 = no important drift, 1 = warning-level, 2 = high-risk, 3 = critical
_EXIT_BAND = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 1,
    Severity.HIGH: 2,
    Severity.CRITICAL: 3,
}


class SemanticDrift(BaseModel):
    drift_type: DriftType
    original_requirement_id: str | None = None
    current_requirement_id: str | None = None
    severity: Severity = Severity.MEDIUM
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    explanation: str = ""
    evidence_original: str | None = None
    evidence_current: str | None = None
    # Human-readable change, e.g. "prohibit -> allow" or "MUST -> SHOULD".
    transformation: str | None = None

    @property
    def label(self) -> str:
        return self.drift_type.value.replace("_", " ").upper()


class DriftReport(BaseModel):
    version: str = "0.1"
    original_source: str = ""
    current_source: str = ""
    integrity_score: float = Field(default=1.0, ge=0.0, le=1.0)
    drifts: list[SemanticDrift] = Field(default_factory=list)
    preserved_pairs: list[tuple[str, str]] = Field(default_factory=list)
    total_original: int = 0
    total_current: int = 0
    matched: int = 0

    def max_severity(self) -> Severity | None:
        if not self.drifts:
            return None
        return max(self.drifts, key=lambda d: d.severity.rank).severity

    def counts_by_severity(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for d in self.drifts:
            out[d.severity.value] = out.get(d.severity.value, 0) + 1
        return out

    def exit_code(self, fail_on: str | Severity = "high") -> int:
        """CI-friendly exit code honoring a --fail-on threshold."""
        if fail_on in ("none", "never"):
            return 0
        threshold = Severity(fail_on) if isinstance(fail_on, str) else fail_on
        worst = self.max_severity()
        if worst is None or worst.rank < threshold.rank:
            return 0
        return _EXIT_BAND[worst]
