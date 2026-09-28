"""Severity assignment for drift types (Section 16 of the plan)."""
from __future__ import annotations

from meaninghash.models import DriftType, Requirement, RequirementKind, Severity, Strength


def severity_for(
    drift_type: DriftType, requirement: Requirement | None = None
) -> Severity:
    """Deterministic severity for a drift, informed by the requirement kind."""
    kind = requirement.kind if requirement else None
    if drift_type in (DriftType.CONSTRAINT_REVERSAL, DriftType.GOAL_CHANGED):
        return Severity.CRITICAL
    if drift_type == DriftType.INTERNAL_CONFLICT:
        return Severity.HIGH
    if drift_type == DriftType.REQUIREMENT_DROPPED:
        if kind == RequirementKind.GOAL:
            return Severity.CRITICAL
        if kind == RequirementKind.CONSTRAINT:
            return Severity.HIGH
        if kind == RequirementKind.PERMISSION:
            return Severity.MEDIUM
        return Severity.LOW
    if drift_type == DriftType.CONSTRAINT_WEAKENED:
        hardened = (
            kind == RequirementKind.CONSTRAINT
            and requirement is not None
            and requirement.strength == Strength.HARD
        )
        return Severity.HIGH if hardened else Severity.MEDIUM
    if drift_type == DriftType.CONSTRAINT_STRENGTHENED:
        return Severity.MEDIUM if kind == RequirementKind.PREFERENCE else Severity.LOW
    if drift_type == DriftType.SCOPE_NARROWED:
        return Severity.HIGH
    if drift_type == DriftType.SCOPE_EXPANDED:
        return Severity.LOW
    if drift_type == DriftType.UNSUPPORTED_ADDITION:
        return Severity.MEDIUM
    return Severity.INFO
