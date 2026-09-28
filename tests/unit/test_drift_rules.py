"""Unit tests for drift classification rules (plan Sections 15-16)."""
import pytest

from meaninghash.drift import (
    classify_added,
    classify_change,
    classify_dropped,
    scope_change,
)
from meaninghash.models import (
    CanonicalForm,
    DriftType,
    Polarity,
    Priority,
    Requirement,
    RequirementKind,
    Severity,
    Strength,
)


def make_req(
    rid="C001",
    kind=RequirementKind.CONSTRAINT,
    subject="photo",
    relation="remain",
    object_="local",
    polarity=Polarity.REQUIRE,
    strength=Strength.HARD,
    scope=None,
    text=None,
    priority=Priority.MEDIUM,
):
    text = text if text is not None else f"{subject} {relation} {object_}"
    return Requirement(
        id=rid,
        kind=kind,
        text=text,
        canonical=CanonicalForm(
            subject=subject, relation=relation, object=object_, polarity=polarity
        ),
        strength=strength,
        priority=priority,
        scope=scope or [],
        confidence=1.0,
    )


class TestStrengthChanges:
    def test_must_to_should_is_weakened(self):
        drift = classify_change(
            make_req(strength=Strength.HARD), make_req(strength=Strength.SOFT)
        )
        assert drift.drift_type == DriftType.CONSTRAINT_WEAKENED
        assert drift.transformation == "MUST -> SHOULD"
        assert drift.severity == Severity.HIGH

    def test_should_to_must_is_strengthened(self):
        drift = classify_change(
            make_req(strength=Strength.SOFT), make_req(strength=Strength.HARD)
        )
        assert drift.drift_type == DriftType.CONSTRAINT_STRENGTHENED
        assert drift.severity == Severity.LOW  # strengthening never violates intent

    def test_strengthened_preference_is_medium(self):
        old = make_req(kind=RequirementKind.PREFERENCE, polarity=Polarity.PREFER,
                       strength=Strength.SOFT)
        new = make_req(kind=RequirementKind.CONSTRAINT, polarity=Polarity.REQUIRE,
                       strength=Strength.HARD)
        drift = classify_change(old, new)
        assert drift.drift_type == DriftType.CONSTRAINT_STRENGTHENED
        assert drift.severity == Severity.MEDIUM


class TestPolarityChanges:
    def test_prohibit_to_allow_is_reversal(self):
        old = make_req(polarity=Polarity.PROHIBIT, relation="delete",
                       subject="original_photo", object_="")
        new = make_req(polarity=Polarity.ALLOW, relation="delete",
                       subject="original_photo", object_="")
        drift = classify_change(old, new)
        assert drift.drift_type == DriftType.CONSTRAINT_REVERSAL
        assert drift.severity == Severity.CRITICAL

    def test_require_to_prefer_is_weakened(self):
        drift = classify_change(make_req(polarity=Polarity.REQUIRE),
                                make_req(polarity=Polarity.PREFER))
        assert drift.drift_type == DriftType.CONSTRAINT_WEAKENED

    def test_prefer_to_require_is_strengthened(self):
        drift = classify_change(make_req(polarity=Polarity.PREFER),
                                make_req(polarity=Polarity.REQUIRE))
        assert drift.drift_type == DriftType.CONSTRAINT_STRENGTHENED

    def test_antonym_flip_preserves_meaning(self):
        # "never delete" == "must preserve" -- no drift.
        old = make_req(polarity=Polarity.PROHIBIT, relation="delete",
                       subject="original_photo", object_="")
        new = make_req(polarity=Polarity.REQUIRE, relation="preserve",
                       subject="original_photo", object_="")
        assert classify_change(old, new) is None


class TestKindChanges:
    def test_constraint_to_preference_is_weakened(self):
        drift = classify_change(
            make_req(kind=RequirementKind.CONSTRAINT),
            make_req(kind=RequirementKind.PREFERENCE),
        )
        assert drift.drift_type == DriftType.CONSTRAINT_WEAKENED

    def test_preference_to_constraint_is_strengthened(self):
        drift = classify_change(
            make_req(kind=RequirementKind.PREFERENCE, polarity=Polarity.PREFER),
            make_req(kind=RequirementKind.CONSTRAINT, polarity=Polarity.REQUIRE),
        )
        assert drift.drift_type == DriftType.CONSTRAINT_STRENGTHENED

    def test_any_goal_kind_change_is_goal_changed(self):
        drift = classify_change(
            make_req(kind=RequirementKind.GOAL),
            make_req(kind=RequirementKind.CONSTRAINT),
        )
        assert drift.drift_type == DriftType.GOAL_CHANGED


class TestGoalChanges:
    def test_identical_goals_preserved(self):
        old = make_req("G001", kind=RequirementKind.GOAL, subject="photo_organizer",
                      relation="build", object_="", polarity=Polarity.STATE,
                      text="Build a photo organizer.")
        assert classify_change(old, old) is None

    def test_changed_goal_subject(self):
        old = make_req("G001", kind=RequirementKind.GOAL, subject="photo_organizer",
                      relation="build", object_="", text="Build a photo organizer.")
        new = make_req("G001", kind=RequirementKind.GOAL, subject="music_player",
                      relation="build", object_="", text="Build a music player.")
        drift = classify_change(old, new)
        assert drift.drift_type == DriftType.GOAL_CHANGED
        assert drift.severity == Severity.CRITICAL


class TestScopeChanges:
    @pytest.mark.parametrize(
        "old,new,expected",
        [
            ([], [], None),
            (["all"], ["all"], None),
            ([], ["all"], None),          # "All X" restates an unqualified claim
            (["all"], ["some"], DriftType.SCOPE_NARROWED),
            (["some"], ["all"], DriftType.SCOPE_EXPANDED),
            (["all"], ["recent"], DriftType.SCOPE_NARROWED),
            (["all", "recent"], ["all"], DriftType.SCOPE_NARROWED),
        ],
    )
    def test_scope_change(self, old, new, expected):
        assert scope_change(old, new) is expected

    def test_narrowed_scope_detected(self):
        drift = classify_change(make_req(scope=["all"]), make_req(scope=["some"]))
        assert drift.drift_type == DriftType.SCOPE_NARROWED
        assert drift.severity == Severity.HIGH


class TestDroppedAndAdded:
    def test_dropped_goal_is_goal_changed(self):
        drift = classify_dropped(make_req("G001", kind=RequirementKind.GOAL))
        assert drift.drift_type == DriftType.GOAL_CHANGED
        assert drift.severity == Severity.CRITICAL
        assert drift.evidence_current is None

    def test_dropped_constraint_is_high(self):
        drift = classify_dropped(make_req("C001"))
        assert drift.drift_type == DriftType.REQUIREMENT_DROPPED
        assert drift.severity == Severity.HIGH

    def test_dropped_permission_is_medium(self):
        drift = classify_dropped(make_req("P001", kind=RequirementKind.PERMISSION))
        assert drift.severity == Severity.MEDIUM

    def test_added_is_unsupported_addition(self):
        drift = classify_added(make_req("P001", kind=RequirementKind.PERMISSION))
        assert drift.drift_type == DriftType.UNSUPPORTED_ADDITION
        assert drift.evidence_original is None
        assert drift.severity == Severity.MEDIUM

