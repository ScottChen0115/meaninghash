"""Unit tests for the Semantic Integrity Score (plan Section 20)."""
from meaninghash.models import (
    DriftType,
    Requirement,
    RequirementKind,
    SemanticContract,
    SemanticDrift,
    Severity,
)
from meaninghash.scoring import SEVERITY_DAMAGE, SIDELINE_DAMAGE, compute_integrity


def contract_of(*weights_reqs):
    reqs = []
    for i, (kind, priority) in enumerate(weights_reqs):
        reqs.append(
            Requirement(id=f"R{i:03d}", kind=kind, text=f"req {i}", priority=priority)
        )
    return SemanticContract(requirements=reqs)


def drift(severity, original_id=None, drift_type=DriftType.CONSTRAINT_WEAKENED):
    return SemanticDrift(
        drift_type=drift_type, severity=severity, original_requirement_id=original_id
    )


class TestSeverityDamageTable:
    def test_monotonic(self):
        order = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH,
                 Severity.CRITICAL]
        values = [SEVERITY_DAMAGE[s] for s in order]
        assert values == sorted(values)
        assert SEVERITY_DAMAGE[Severity.CRITICAL] == 1.0
        assert SEVERITY_DAMAGE[Severity.INFO] == 0.0


class TestComputeIntegrity:
    def test_no_drifts_is_perfect(self):
        c = contract_of((RequirementKind.GOAL, "high"))
        assert compute_integrity(c, []) == 1.0

    def test_empty_contract_is_perfect(self):
        assert compute_integrity(contract_of(), [drift(Severity.CRITICAL)]) == 1.0

    def test_total_damage_floors_at_zero(self):
        c = contract_of((RequirementKind.CONSTRAINT, "medium"))  # weight 8
        drifts = [
            drift(Severity.CRITICAL, "R000"),
            drift(Severity.HIGH, "R000"),   # damage caps at total weight
        ]
        assert compute_integrity(c, drifts) == 0.0

    def test_half_damage(self):
        c = contract_of((RequirementKind.GOAL, "high"))  # weight 10
        # HIGH drift damages 50% of the goal's weight.
        assert compute_integrity(c, [drift(Severity.HIGH, "R000")]) == 0.5

    def test_sideline_damage_for_additions(self):
        c = contract_of((RequirementKind.GOAL, "high"))  # total 10
        # Addition has no original requirement -> 3.0 * 0.25 = 0.75 damage.
        score = compute_integrity(
            c, [drift(Severity.MEDIUM, None, DriftType.UNSUPPORTED_ADDITION)]
        )
        assert score == round(1.0 - SIDELINE_DAMAGE * 0.25 / 10, 4)

    def test_score_within_bounds(self):
        c = contract_of((RequirementKind.GOAL, "high"),
                        (RequirementKind.CONSTRAINT, "high"),
                        (RequirementKind.PERMISSION, "medium"))
        drifts = [drift(Severity.MEDIUM, "R001"), drift(Severity.LOW, "R002")]
        score = compute_integrity(c, drifts)
        assert 0.0 <= score <= 1.0
