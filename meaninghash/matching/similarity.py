"""Weighted requirement similarity (plan Section 13).

Compares requirements in canonical space -- the deterministic heart of
MeaningHash. Weights: subject .25 / relation .25 / object .15 / scope .15 /
surface text .20.
"""
from __future__ import annotations

from dataclasses import dataclass

from meaninghash.extraction.normalization import jaccard, overlap, phrase_similarity
from meaninghash.models import Requirement


@dataclass(frozen=True)
class SimilarityWeights:
    subject: float = 0.25
    relation: float = 0.25
    object: float = 0.15
    scope: float = 0.15
    text: float = 0.20


def scope_similarity(a: list[str], b: list[str]) -> float:
    """Scope qualifier similarity; qualified vs unqualified = mild 0.5."""
    ta, tb = set(a), set(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.5
    return max(jaccard(ta, tb), overlap(ta, tb))


def requirement_similarity(
    a: Requirement,
    b: Requirement,
    weights: SimilarityWeights = SimilarityWeights(),
) -> float:
    """Weighted similarity in [0, 1] between two requirements."""
    return (
        weights.subject * phrase_similarity(a.canonical.subject, b.canonical.subject)
        + weights.relation * phrase_similarity(a.canonical.relation, b.canonical.relation)
        + weights.object * phrase_similarity(a.canonical.object, b.canonical.object)
        + weights.scope * scope_similarity(a.scope, b.scope)
        + weights.text * phrase_similarity(a.text, b.text)
    )
