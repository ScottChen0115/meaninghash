"""Unit tests for SemanticExtractor validation and retry behavior."""
import pytest

from meaninghash.extraction import ExtractionError, SemanticExtractor
from meaninghash.providers.base import ExtractionProvider, ProviderError
from meaninghash.providers.mock import MockProvider

DEMO = (
    "Build a photo organizer.\n"
    "All photos must stay on the user's Mac.\n"
    "Never delete the original photos.\n"
    "Duplicates may be moved into a separate folder.\n"
    "Prefer Python.\n"
)

VALID = {
    "goals": [
        {"text": "Build a photo organizer.",
         "canonical": {"subject": "photo_organizer", "relation": "build",
                       "object": "", "polarity": "state"},
         "strength": "hard", "priority": "high", "scope": [], "confidence": 0.95}
    ],
    "constraints": [], "permissions": [], "preferences": [], "assumptions": [],
}


class FlakyProvider(ExtractionProvider):
    name = "flaky"

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0
        self.feedback_errors: list[list[str]] = []

    def extract_raw(self, text: str) -> dict:
        self.calls += 1
        if self.calls <= self.failures:
            return "not-a-dict"  # invalid shape
        return VALID

    def extract_raw_with_feedback(self, text: str, errors: list[str]) -> dict:
        self.feedback_errors.append(list(errors))
        return self.extract_raw(text)


class ExplodingProvider(ExtractionProvider):
    name = "exploding"

    def extract_raw(self, text: str) -> dict:
        raise ProviderError("model overloaded")


class TestMockExtraction:
    def test_demo_contract_shape(self):
        contract = SemanticExtractor(MockProvider()).extract(DEMO, source_id="demo")
        assert [r.id for r in contract.requirements] == [
            "G001", "C001", "C002", "P001", "PR001",
        ]
        assert contract.source.source_id == "demo"

    def test_empty_text_yields_empty_contract(self):
        contract = SemanticExtractor(MockProvider()).extract("", source_id="empty")
        assert contract.requirements == []

    def test_unknown_group_keys_ignored(self):
        class Noisy(ExtractionProvider):
            name = "noisy"

            def extract_raw(self, text):
                return {"goals": VALID["goals"], "chatter": ["x"], "constraints": None}

        contract = SemanticExtractor(Noisy()).extract("anything")
        assert len(contract.requirements) == 1


class TestRetries:
    def test_recovers_after_invalid_output(self):
        provider = FlakyProvider(failures=1)
        contract = SemanticExtractor(provider).extract(DEMO)
        assert provider.calls == 2
        assert provider.feedback_errors and provider.feedback_errors[0]
        assert len(contract.requirements) == 1

    def test_gives_up_after_max_retries(self):
        provider = FlakyProvider(failures=99)
        with pytest.raises(ExtractionError, match="after 3 attempts"):
            SemanticExtractor(provider).extract(DEMO)
        assert provider.calls == 3

    def test_provider_error_retried_then_raised(self):
        with pytest.raises(ExtractionError, match="model overloaded"):
            SemanticExtractor(ExplodingProvider()).extract(DEMO)


class TestValidation:
    def test_duplicate_provider_ids_are_regenerated(self):
        payload = {
            "goals": [
                {"id": "G001", "text": "a",
                 "canonical": {"subject": "", "relation": "", "object": "",
                               "polarity": "state"}},
                {"id": "G001", "text": "b",
                 "canonical": {"subject": "", "relation": "", "object": "",
                               "polarity": "state"}},
            ]
        }

        class Fixed(ExtractionProvider):
            name = "fixed"

            def extract_raw(self, text):
                return payload

        contract = SemanticExtractor(Fixed()).extract("x")
        assert [r.id for r in contract.requirements] == ["G001", "G002"]

    def test_bad_enum_rejected(self):
        payload = {
            "goals": [
                {"text": "a", "canonical": {"polarity": "maybe"}},
            ]
        }

        class Fixed(ExtractionProvider):
            name = "fixed"

            def extract_raw(self, text):
                return payload

        with pytest.raises(ExtractionError):
            SemanticExtractor(Fixed()).extract("x")
