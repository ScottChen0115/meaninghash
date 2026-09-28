"""Unit tests for the DriftDetector engine and internal-conflict logic."""
from meaninghash.drift import DriftDetector, detect_internal_conflicts
from meaninghash.extraction import SemanticExtractor
from meaninghash.models import (
    CanonicalForm,
    ContractSource,
    Polarity,
    Requirement,
    RequirementKind,
    SemanticContract,
    Severity,
)
from meaninghash.providers.mock import MockProvider


def make_req(rid, kind=RequirementKind.CONSTRAINT, subject="data", relation="remain",
             object_="local", polarity=Polarity.REQUIRE, text=None):
    text = text or f"{subject} {relation} {object_}"
    return Requirement(
        id=rid, kind=kind, text=text,
        canonical=CanonicalForm(subject=subject, relation=relation,
                                object=object_, polarity=polarity),
    )


def contract(reqs, source_id="doc"):
    return SemanticContract(
        source=ContractSource(source_id=source_id), requirements=reqs
    )


class TestInternalConflicts:
    def test_local_only_vs_upload(self):
        c = contract([
            make_req("C001", subject="data", relation="remain", object_="local"),
            make_req("C002", subject="log", relation="upload", object_="cloud"),
        ])
        conflicts = detect_internal_conflicts(c)
        assert len(conflicts) == 1
        assert conflicts[0].severity == Severity.HIGH
        assert "local" in conflicts[0].explanation

    def test_opposite_polarity_same_relation(self):
        c = contract([
            make_req("C001", subject="photo", relation="delete", object_="",
                     polarity=Polarity.PROHIBIT),
            make_req("P001", kind=RequirementKind.PERMISSION, subject="photo",
                     relation="delete", object_="", polarity=Polarity.ALLOW),
        ])
        assert len(detect_internal_conflicts(c)) == 1

    def test_complementary_requirements_no_conflict(self):
        c = contract([
            make_req("C001", subject="photo", relation="remain", object_="local"),
            make_req("P001", kind=RequirementKind.PERMISSION, subject="duplicate",
                     relation="move", object_="folder", polarity=Polarity.ALLOW),
        ])
        assert detect_internal_conflicts(c) == []


class TestDetector:
    def test_identical_contracts_fully_preserved(self):
        text = ("Build a photo organizer.\n"
                "All photos must stay on the user's Mac.\n"
                "Never delete the original photos.\n"
                "Prefer Python.\n")
        extractor = SemanticExtractor(MockProvider())
        original = extractor.extract(text, source_id="v1")
        current = extractor.extract(text, source_id="v2")
        report = DriftDetector().compare(original, current)
        assert report.drifts == []
        assert report.integrity_score == 1.0
        assert len(report.preserved_pairs) == len(original.requirements)
        assert report.total_original == report.total_current == report.matched

    def test_source_labels(self):
        original = contract([make_req("C001")], source_id="spec-v1.md")
        current = contract([make_req("C001")], source_id="spec-v2.md")
        report = DriftDetector().compare(original, current)
        assert report.original_source == "spec-v1.md"
        assert report.current_source == "spec-v2.md"

    def test_drifts_sorted_by_severity(self):
        original = contract([
            make_req("C001", subject="password", relation="delete", object_=""),
            make_req("C002", subject="photo", relation="remain", object_="local"),
        ])
        current = contract([
            make_req("C001", subject="password", relation="delete", object_="",
                     polarity=Polarity.ALLOW),          # reversal (critical)
            make_req("C002", subject="photo", relation="remain", object_="local",
                     polarity=Polarity.ALLOW),          # reversal (critical)
        ])
        report = DriftDetector().compare(original, current)
        assert all(
            a.severity.rank >= b.severity.rank
            for a, b in zip(report.drifts, report.drifts[1:])
        )

    def test_empty_contracts(self):
        report = DriftDetector().compare(contract([]), contract([]))
        assert report.drifts == []
        assert report.integrity_score == 1.0
        assert report.total_original == 0
