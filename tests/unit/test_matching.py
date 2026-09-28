"""Unit tests for weighted similarity and 1:1 alignment."""
from meaninghash.matching import RequirementMatcher, align, requirement_similarity
from meaninghash.matching.similarity import scope_similarity
from meaninghash.models import CanonicalForm, Polarity, Requirement, RequirementKind


def req(rid, subject="", relation="", object_="", text="", scope=None, kind=None):
    return Requirement(
        id=rid,
        kind=kind or RequirementKind.CONSTRAINT,
        text=text or f"{subject} {relation} {object_}".strip(),
        canonical=CanonicalForm(
            subject=subject, relation=relation, object=object_, polarity=Polarity.REQUIRE
        ),
        scope=scope or [],
    )


class TestSimilarity:
    def test_identical(self):
        a = req("A", "photo", "remain", "local", "photos must stay local")
        assert requirement_similarity(a, a) == 1.0

    def test_unrelated(self):
        a = req("A", "password", "delete", "", "delete passwords")
        b = req("B", "photo", "remain", "local", "photos stay local")
        assert requirement_similarity(a, b) < 0.3

    def test_scope_similarity(self):
        assert scope_similarity(["all"], ["all"]) == 1.0
        assert scope_similarity([], []) == 1.0
        assert scope_similarity(["all"], []) == 0.5
        assert scope_similarity(["all"], ["some"]) == 0.0


class TestAlignment:
    def test_matched_pair(self):
        a = req("A", "photo", "remain", "local", "all photos must stay on the mac")
        b = req("B", "photo", "remain", "local", "photos stay on the mac")
        result = align([a], [b], threshold=0.55)
        assert [(m.original_id, m.current_id) for m in result.matches] == [("A", "B")]
        assert result.unmatched_original == []
        assert result.unmatched_current == []

    def test_below_threshold_unmatched(self):
        a = req("A", "password", "delete", "", "delete passwords")
        b = req("B", "photo", "remain", "local", "photos stay local")
        result = align([a], [b])
        assert result.matches == []
        assert result.unmatched_original == ["A"]
        assert result.unmatched_current == ["B"]

    def test_one_to_one_greedy(self):
        # Two originals both resemble the single current one; best wins.
        weak = req("A", "photo", "remain", "cloud", "photos stay in the cloud")
        strong = req("B", "photo", "remain", "local", "photos stay on the mac")
        current = req("C", "photo", "remain", "local", "photos stay on the mac")
        result = align([weak, strong], [current])
        assert [(m.original_id, m.current_id) for m in result.matches] == [("B", "C")]
        assert result.unmatched_original == ["A"]

    def test_matcher_facade(self):
        from meaninghash.models import ContractSource, SemanticContract

        original = SemanticContract(
            source=ContractSource(source_id="o"),
            requirements=[req("A", "photo", "remain", "local", "photos stay local")],
        )
        current = SemanticContract(
            source=ContractSource(source_id="c"),
            requirements=[req("B", "photo", "remain", "local", "photos stay local")],
        )
        result = RequirementMatcher().match(original, current)
        assert len(result.matches) == 1

    def test_empty_contracts(self):
        result = align([], [])
        assert result.matches == []
        assert result.unmatched_original == []
        assert result.unmatched_current == []
