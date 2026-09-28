"""Drift classification rules (Sections 15-16 of the plan).

Order of checks for an aligned pair:
1. goal change          4. strength (MUST -> SHOULD / SHOULD -> MUST)
2. polarity reversal    5. scope narrowing / expansion
3. kind change
"""
from __future__ import annotations

from meaninghash.drift.severity import severity_for
from meaninghash.extraction.normalization import phrase_similarity, relation_antonym
from meaninghash.models import (
    DriftType,
    Polarity,
    Requirement,
    RequirementKind,
    SemanticDrift,
    Strength,
)

# Polarity flips that reverse the meaning of a requirement.
_REVERSAL_PAIRS = {
    frozenset({Polarity.PROHIBIT, Polarity.ALLOW}),
    frozenset({Polarity.PROHIBIT, Polarity.REQUIRE}),
    frozenset({Polarity.PROHIBIT, Polarity.PREFER}),
}

_BROADNESS = {"all": 3, "every": 3, "most": 2, "some": 1, "any": 1,
              "only": 1, "selected": 1, "recent": 1}


def _broadness(scope: list[str]) -> int:
    return max((_BROADNESS.get(tag, 2) for tag in scope), default=2)


def scope_change(old: list[str], new: list[str]) -> DriftType | None:
    """Compare scope qualifier sets; None when meaning-preserving."""
    if not old and not new:
        return None
    if not old and set(new) <= {"all"}:
        return None  # "All X..." restates an unqualified statement
    bo, bn = _broadness(old), _broadness(new)
    if bn < bo:
        return DriftType.SCOPE_NARROWED
    if bn > bo:
        return DriftType.SCOPE_EXPANDED
    to, tn = set(old), set(new)
    if tn < to:
        return DriftType.SCOPE_NARROWED
    if to < tn:
        return DriftType.SCOPE_EXPANDED
    return None


def classify_change(old: Requirement, new: Requirement) -> SemanticDrift | None:
    """Classify drift between two aligned requirements (None = preserved)."""
    drift_type, transformation = _classify(old, new)
    if drift_type is None:
        return None
    return SemanticDrift(
        drift_type=drift_type,
        original_requirement_id=old.id,
        current_requirement_id=new.id,
        severity=severity_for(drift_type, old),
        confidence=round(min(old.confidence, new.confidence), 2),
        evidence_original=old.text,
        evidence_current=new.text,
        transformation=transformation,
    )


def _classify(old: Requirement, new: Requirement) -> tuple[DriftType | None, str | None]:
    op, np_ = old.canonical.polarity, new.canonical.polarity

    # 1. Goals: a changed goal is the most fundamental drift there is.
    if old.kind == RequirementKind.GOAL and new.kind == RequirementKind.GOAL:
        if (
            phrase_similarity(old.canonical.subject, new.canonical.subject) < 0.4
            or phrase_similarity(old.text, new.text) < 0.6
        ):
            return DriftType.GOAL_CHANGED, "goal subject changed"
        return None, None

    # 2. Polarity flips.
    if op != np_:
        pair = frozenset({op, np_})
        if (
            pair == frozenset({Polarity.PROHIBIT, Polarity.REQUIRE})
            and relation_antonym(old.canonical.relation, new.canonical.relation)
        ):
            return None, None  # "never delete" == "must preserve"
        if pair in _REVERSAL_PAIRS:
            return DriftType.CONSTRAINT_REVERSAL, f"{op.value} -> {np_.value}"
        if (op, np_) == (Polarity.PREFER, Polarity.REQUIRE):
            return DriftType.CONSTRAINT_STRENGTHENED, "prefer -> require"
        if (op, np_) == (Polarity.REQUIRE, Polarity.PREFER):
            return DriftType.CONSTRAINT_WEAKENED, "require -> prefer"

    # 3. Kind downgrades / upgrades.
    if old.kind != new.kind:
        if old.kind == RequirementKind.CONSTRAINT and new.kind in (
            RequirementKind.PREFERENCE,
            RequirementKind.PERMISSION,
        ):
            return DriftType.CONSTRAINT_WEAKENED, f"{old.kind.value} -> {new.kind.value}"
        if new.kind == RequirementKind.CONSTRAINT and old.kind in (
            RequirementKind.PREFERENCE,
            RequirementKind.PERMISSION,
        ):
            return DriftType.CONSTRAINT_STRENGTHENED, f"{old.kind.value} -> {new.kind.value}"
        if RequirementKind.GOAL in (old.kind, new.kind):
            return DriftType.GOAL_CHANGED, f"{old.kind.value} -> {new.kind.value}"

    # 4. Strength: the plan's core example (MUST -> SHOULD weakens).
    if old.strength == Strength.HARD and new.strength == Strength.SOFT:
        return DriftType.CONSTRAINT_WEAKENED, "MUST -> SHOULD"
    if old.strength == Strength.SOFT and new.strength == Strength.HARD:
        return DriftType.CONSTRAINT_STRENGTHENED, "SHOULD -> MUST"

    # 5. Scope.
    sc = scope_change(old.scope, new.scope)
    if sc is not None:
        return sc, f"scope {old.scope or '{}'} -> {new.scope or '{}'}"

    return None, None


def classify_dropped(req: Requirement) -> SemanticDrift:
    drift_type = (
        DriftType.GOAL_CHANGED
        if req.kind == RequirementKind.GOAL
        else DriftType.REQUIREMENT_DROPPED
    )
    return SemanticDrift(
        drift_type=drift_type,
        original_requirement_id=req.id,
        severity=severity_for(drift_type, req),
        confidence=req.confidence,
        explanation=(
            f"{req.kind.value} {req.id} was dropped in the current version."
        ),
        evidence_original=req.text,
        evidence_current=None,
        transformation="present -> absent",
    )


def classify_added(req: Requirement) -> SemanticDrift:
    return SemanticDrift(
        drift_type=DriftType.UNSUPPORTED_ADDITION,
        current_requirement_id=req.id,
        severity=severity_for(DriftType.UNSUPPORTED_ADDITION, req),
        confidence=req.confidence,
        explanation=(
            f"{req.kind.value} {req.id} appears only in the current version "
            "and was never agreed to."
        ),
        evidence_original=None,
        evidence_current=req.text,
        transformation="absent -> present",
    )
