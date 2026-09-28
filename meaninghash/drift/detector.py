"""DriftDetector: contracts in, DriftReport out (Stage 4 of the pipeline)."""
from __future__ import annotations

from meaninghash.drift.rules import classify_added, classify_change, classify_dropped
from meaninghash.extraction.normalization import phrase_similarity
from meaninghash.matching import RequirementMatcher
from meaninghash.models import (
    CanonicalForm,
    DriftReport,
    DriftType,
    Polarity,
    Requirement,
    SemanticContract,
    SemanticDrift,
    Severity,
)
from meaninghash.scoring.integrity import compute_integrity


class DriftDetector:
    """Deterministic comparison of two Semantic Contracts."""

    def __init__(self, alignment_threshold: float = 0.55) -> None:
        self.matcher = RequirementMatcher(alignment_threshold)

    def compare(
        self, original: SemanticContract, current: SemanticContract
    ) -> DriftReport:
        alignment = self.matcher.match(original, current)
        drifts: list[SemanticDrift] = []
        preserved: list[tuple[str, str]] = []

        for pair in alignment.matches:
            old = original.get(pair.original_id)
            new = current.get(pair.current_id)
            drift = classify_change(old, new)
            if drift is None:
                preserved.append((pair.original_id, pair.current_id))
            else:
                drifts.append(drift)

        for rid in alignment.unmatched_original:
            drifts.append(classify_dropped(original.get(rid)))
        for rid in alignment.unmatched_current:
            drifts.append(classify_added(current.get(rid)))

        drifts.extend(detect_internal_conflicts(current))
        drifts.sort(key=lambda d: (-d.severity.rank, d.drift_type.value))

        return DriftReport(
            original_source=_source_label(original),
            current_source=_source_label(current),
            integrity_score=compute_integrity(original, drifts),
            drifts=drifts,
            preserved_pairs=preserved,
            total_original=len(original.requirements),
            total_current=len(current.requirements),
            matched=len(alignment.matches),
        )


def _source_label(contract: SemanticContract) -> str:
    return contract.source.source_id or contract.source.path or contract.source.type


# -- internal conflict detection (Section 15.8) ----------------------------
_CONFLICT_PAIRS = {
    frozenset({Polarity.PROHIBIT, Polarity.REQUIRE}),
    frozenset({Polarity.PROHIBIT, Polarity.ALLOW}),
}
_LOCAL_RELATIONS = {"remain", "store", "process"}
_EXTERNAL_RELATIONS = {"upload", "send", "share"}


def detect_internal_conflicts(contract: SemanticContract) -> list[SemanticDrift]:
    """Contradictions inside a single contract (e.g. local vs upload)."""
    conflicts: list[SemanticDrift] = []
    reqs = contract.requirements
    for i, a in enumerate(reqs):
        for b in reqs[i + 1:]:
            reason = _pair_conflict(a, b)
            if reason:
                conflicts.append(
                    SemanticDrift(
                        drift_type=DriftType.INTERNAL_CONFLICT,
                        current_requirement_id=b.id,
                        severity=Severity.HIGH,
                        confidence=0.85,
                        explanation=reason,
                        evidence_original=a.text,
                        evidence_current=b.text,
                        transformation="contradiction",
                    )
                )
    return conflicts


def _pair_conflict(a: Requirement, b: Requirement) -> str | None:
    ca, cb = a.canonical, b.canonical
    # Same relation, opposite polarity, similar subject.
    if ca.relation and ca.relation == cb.relation:
        pair = frozenset({ca.polarity, cb.polarity})
        if pair in _CONFLICT_PAIRS:
            if phrase_similarity(ca.subject, cb.subject) > 0.3:
                return (
                    f"{a.id} and {b.id} both govern "
                    f"'{ca.subject or ca.relation}' with opposite polarity "
                    f"({ca.polarity.value} vs {cb.polarity.value})."
                )
    # Local-processing guard vs external transmission.
    if _is_local_guard(ca) and _is_external_release(cb):
        return (
            f"{a.id} requires data to remain local, but {b.id} "
            f"{cb.relation}s it to an external destination."
        )
    if _is_local_guard(cb) and _is_external_release(ca):
        return (
            f"{b.id} requires data to remain local, but {a.id} "
            f"{ca.relation}s it to an external destination."
        )
    return None


def _is_local_guard(c: CanonicalForm) -> bool:
    return (
        c.relation in _LOCAL_RELATIONS
        and c.object == "local"
        and c.polarity == Polarity.REQUIRE
    )


def _is_external_release(c: CanonicalForm) -> bool:
    return c.relation in _EXTERNAL_RELATIONS and c.polarity in (
        Polarity.REQUIRE,
        Polarity.ALLOW,
    )

