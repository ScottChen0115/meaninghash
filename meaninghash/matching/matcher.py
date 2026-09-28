"""Contract-level matching facade."""
from __future__ import annotations

from meaninghash.matching.alignment import AlignmentResult, MatchPair, align
from meaninghash.models import SemanticContract

__all__ = ["RequirementMatcher", "AlignmentResult", "MatchPair", "align"]


class RequirementMatcher:
    def __init__(self, threshold: float = 0.55) -> None:
        self.threshold = threshold

    def match(
        self, original: SemanticContract, current: SemanticContract
    ) -> AlignmentResult:
        return align(
            original.requirements, current.requirements, self.threshold
        )
