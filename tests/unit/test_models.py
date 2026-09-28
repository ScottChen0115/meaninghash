"""Unit tests for the core data models."""
import pytest

from meaninghash.models import (
    CanonicalForm,
    DriftReport,
    Polarity,
    Priority,
    Requirement,
    RequirementKind,
    SemanticContract,
    SemanticDrift,
    Severity,
    Strength,
    next_requirement_id,
)


def req(kind=RequirementKind.CONSTRAINT, priority=Priority.MEDIUM, **kw):
    return Requirement(
        id=kw.get("id", "C001"),
        kind=kind,
        text=kw.get("text", "photos must stay local"),
        canonical=kw.get("canonical", CanonicalForm()),
        priority=priority,
    )


class TestRequirementIds:
    def test_sequence(self):
        assert next_requirement_id(RequirementKind.CONSTRAINT, []) == "C001"
        assert next_requirement_id(
            RequirementKind.CONSTRAINT, ["C001", "G001"]
        ) == "C002"

    def test_prefixes(self):
        assert next_requirement_id(RequirementKind.GOAL, []).startswith("G")
        assert next_requirement_id(RequirementKind.PERMISSION, []).startswith("P")
        assert next_requirement_id(RequirementKind.PREFERENCE, []).startswith("PR")
        assert next_requirement_id(RequirementKind.ASSUMPTION, []).startswith("A")

    def test_duplicate_id_avoided(self):
        assert next_requirement_id(RequirementKind.CONSTRAINT, ["C001"]) == "C002"


class TestWeights:
    def test_kind_weights(self):
        assert req(kind=RequirementKind.GOAL).weight == 10
        assert req(kind=RequirementKind.CONSTRAINT).weight == 8
        assert req(kind=RequirementKind.PERMISSION).weight == 5
        assert req(kind=RequirementKind.PREFERENCE).weight == 2

    def test_critical_priority_overrides(self):
        assert req(priority=Priority.CRITICAL).weight == 10


class TestSeverity:
    def test_at_least(self):
        assert Severity.at_least("high") == [Severity.HIGH, Severity.CRITICAL]
        assert Severity.at_least(Severity.INFO) == list(Severity)

    def test_rank_ordering(self):
        assert Severity.INFO.rank < Severity.LOW.rank < Severity.MEDIUM.rank
        assert Severity.MEDIUM.rank < Severity.HIGH.rank < Severity.CRITICAL.rank


class TestDriftReport:
    def _report(self, *severities):
        return DriftReport(
            drifts=[
                SemanticDrift(drift_type="constraint_weakened", severity=s)
                for s in severities
            ]
        )

    def test_max_severity_empty(self):
        assert self._report().max_severity() is None

    def test_counts(self):
        report = self._report(Severity.LOW, Severity.LOW, Severity.CRITICAL)
        assert report.counts_by_severity() == {"low": 2, "critical": 1}

    @pytest.mark.parametrize(
        "severities,fail_on,expected",
        [
            ([], "high", 0),
            ([Severity.LOW], "high", 0),
            ([Severity.MEDIUM], "medium", 1),
            ([Severity.HIGH], "high", 2),
            ([Severity.LOW, Severity.CRITICAL], "high", 3),
            ([Severity.CRITICAL], "never", 0),
            ([Severity.HIGH], "critical", 0),
        ],
    )
    def test_exit_codes(self, severities, fail_on, expected):
        assert self._report(*severities).exit_code(fail_on) == expected


class TestSemanticContract:
    def test_grouped_views(self):
        contract = SemanticContract(
            requirements=[
                req(id="G001", kind=RequirementKind.GOAL),
                req(id="C001"),
                req(id="C002"),
            ]
        )
        assert [r.id for r in contract.goals] == ["G001"]
        assert [r.id for r in contract.constraints] == ["C001", "C002"]
        assert contract.get("C002") is contract.requirements[2]
        assert contract.get("nope") is None
        assert contract.summary()["total"] == 3

    def test_grouped_dict_roundtrip_shape(self):
        data = SemanticContract(
            requirements=[req(id="C001")]
        ).to_grouped_dict()
        assert set(data) == {
            "version", "source", "goals", "constraints",
            "permissions", "preferences", "assumptions",
        }
        assert data["constraints"][0]["id"] == "C001"

    def test_total_weight(self):
        contract = SemanticContract(
            requirements=[req(id="G001", kind=RequirementKind.GOAL), req(id="C001")]
        )
        assert contract.total_weight() == 18
