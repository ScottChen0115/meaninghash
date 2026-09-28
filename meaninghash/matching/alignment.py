"""One-to-one requirement alignment via greedy best-match (plan Section 12)."""
from __future__ import annotations

from dataclasses import dataclass, field

from meaninghash.matching.similarity import requirement_similarity
from meaninghash.models import Requirement


@dataclass
class MatchPair:
    original_id: str
    current_id: str
    score: float


@dataclass
class AlignmentResult:
    matches: list[MatchPair] = field(default_factory=list)
    unmatched_original: list[str] = field(default_factory=list)
    unmatched_current: list[str] = field(default_factory=list)


def align(
    original: list[Requirement],
    current: list[Requirement],
    threshold: float = 0.55,
) -> AlignmentResult:
    """Greedy 1:1 alignment: highest similarity pairs win."""
    scored: list[tuple[float, int, int]] = []
    for i, a in enumerate(original):
        for j, b in enumerate(current):
            score = requirement_similarity(a, b)
            if score >= threshold:
                scored.append((score, i, j))
    scored.sort(key=lambda t: (-t[0], t[1], t[2]))

    taken_original: set[int] = set()
    taken_current: set[int] = set()
    matches: list[MatchPair] = []
    for score, i, j in scored:
        if i in taken_original or j in taken_current:
            continue
        taken_original.add(i)
        taken_current.add(j)
        matches.append(
            MatchPair(original[i].id, current[j].id, round(score, 4))
        )
    matches.sort(key=lambda m: m.original_id)

    return AlignmentResult(
        matches=matches,
        unmatched_original=[
            r.id for i, r in enumerate(original) if i not in taken_original
        ],
        unmatched_current=[
            r.id for j, r in enumerate(current) if j not in taken_current
        ],
    )
