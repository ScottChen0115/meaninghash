"""Semantic Integrity Score (Section 20 of the plan).

integrity = 1 - damage / total_weight(original)

where each drift damages its original requirement's weight scaled by
severity (critical 100%, high 50%, medium 25%, low 10%) and drifts with
no original requirement (additions, internal conflicts) contribute a
fixed sideline damage.
"""
from __future__ import annotations

from meaninghash.models import SemanticContract, SemanticDrift, Severity

SEVERITY_DAMAGE: dict[Severity, float] = {
    Severity.CRITICAL: 1.0,
    Severity.HIGH: 0.5,
    Severity.MEDIUM: 0.25,
    Severity.LOW: 0.1,
    Severity.INFO: 0.0,
}

SIDELINE_DAMAGE = 3.0


def compute_integrity(
    original: SemanticContract, drifts: list[SemanticDrift]
) -> float:
    total = original.total_weight()
    if total == 0:
        return 1.0
    damage = 0.0
    for drift in drifts:
        req = (
            original.get(drift.original_requirement_id)
            if drift.original_requirement_id
            else None
        )
        factor = SEVERITY_DAMAGE[drift.severity]
        damage += req.weight * factor if req else SIDELINE_DAMAGE * factor
    return round(max(0.0, 1.0 - min(damage, total) / total), 4)
