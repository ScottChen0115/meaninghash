"""Unit tests for the deterministic rule-based parser."""
from meaninghash.extraction.rule_based import analyze_sentence, parse_text, split_sentences

ORIGINAL = """\
Build a photo organizer.
All photos must stay on the user's Mac.
Never delete the original photos.
Duplicates may be moved into a separate folder.
Prefer Python.
"""


class TestSentenceSplitting:
    def test_paragraphs_and_bullets(self):
        text = "First sentence. Second sentence.\n\n- bullet one\n- bullet two"
        sentences = split_sentences(text)
        assert sentences == [
            "First sentence.", "Second sentence.",
            "bullet one", "bullet two",
        ]

    def test_wrapped_lines_joined(self):
        assert split_sentences("photos must\nstay local.") == ["photos must stay local."]


class TestAnalyzeSentence:
    def test_goal(self):
        parsed = analyze_sentence("Build a photo organizer.")
        assert parsed["kind"] == "goal"
        assert parsed["canonical"]["subject"] == "photo_organizer"
        assert parsed["canonical"]["relation"] == "build"
        assert parsed["strength"] == "hard"
        assert parsed["priority"] == "critical"

    def test_hard_requirement_with_scope(self):
        parsed = analyze_sentence("All photos must stay on the user's Mac.")
        c = parsed["canonical"]
        assert parsed["kind"] == "constraint"
        assert c["subject"] == "photo"
        assert c["relation"] == "remain"
        assert c["object"] == "local"
        assert c["polarity"] == "require"
        assert parsed["strength"] == "hard"
        assert parsed["scope"] == ["all"]

    def test_prohibition(self):
        parsed = analyze_sentence("Never delete the original photos.")
        c = parsed["canonical"]
        assert parsed["kind"] == "constraint"
        assert c["subject"] == "original_photo"
        assert c["relation"] == "delete"
        assert c["polarity"] == "prohibit"
        assert parsed["strength"] == "hard"
        assert parsed["priority"] == "high"

    def test_softened_requirement(self):
        parsed = analyze_sentence("Photos should stay on the user's Mac.")
        assert parsed["kind"] == "constraint"
        assert parsed["strength"] == "soft"

    def test_permission(self):
        parsed = analyze_sentence("Duplicates may be moved into a separate folder.")
        c = parsed["canonical"]
        assert parsed["kind"] == "permission"
        assert c["subject"] == "duplicate"
        assert c["relation"] == "move"
        assert c["object"] == "folder"
        assert c["polarity"] == "allow"

    def test_preference(self):
        parsed = analyze_sentence("Prefer Python.")
        c = parsed["canonical"]
        assert parsed["kind"] == "preference"
        assert c["subject"] == "language"
        assert c["relation"] == "prefer"
        assert c["object"] == "python"
        assert c["polarity"] == "prefer"

    def test_chatter_skipped(self):
        assert analyze_sentence("Hello there, thanks a lot!") is None


class TestParseText:
    def test_demo_groups(self):
        contract = parse_text(ORIGINAL)
        assert len(contract["goals"]) == 1
        assert len(contract["constraints"]) == 2
        assert len(contract["permissions"]) == 1
        assert len(contract["preferences"]) == 1
        assert contract["assumptions"] == []
