"""Requirement matching: weighted similarity + 1:1 alignment."""
from meaninghash.matching.alignment import AlignmentResult, MatchPair, align
from meaninghash.matching.matcher import RequirementMatcher
from meaninghash.matching.similarity import (
    SimilarityWeights,
    requirement_similarity,
    scope_similarity,
)

__all__ = [
    "AlignmentResult",
    "MatchPair",
    "align",
    "RequirementMatcher",
    "SimilarityWeights",
    "requirement_similarity",
    "scope_similarity",
]
