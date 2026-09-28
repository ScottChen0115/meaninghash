"""Unit tests for canonicalization / normalization utilities."""
from meaninghash.extraction.normalization import (
    canonical_word,
    jaccard,
    overlap,
    phrase_similarity,
    relation_antonym,
    token_set,
)


class TestCanonicalWord:
    def test_verb_variants_collapse(self):
        assert canonical_word("removes") == "delete"
        assert canonical_word("erased") == "delete"
        assert canonical_word("destroy") == "delete"

    def test_noun_variants_collapse(self):
        assert canonical_word("images") == "photo"
        assert canonical_word("pictures") == "photo"
        assert canonical_word("Master") == "original"

    def test_locations_collapse(self):
        assert canonical_word("mac") == "local"
        assert canonical_word("locally") == "local"
        assert canonical_word("third-party") == "cloud"
        assert canonical_word("servers") == "cloud"

    def test_stopwords_return_none(self):
        assert canonical_word("the") is None
        assert canonical_word("must") is None
        assert canonical_word("never") is None

    def test_unknown_word_passes_through(self):
        assert canonical_word("macguffin") == "macguffin"

    def test_irregular_plural(self):
        # "directories" -> "directory" -> folder
        assert canonical_word("directories") == "folder"


class TestTokenSet:
    def test_underscore_phrases(self):
        assert token_set("original_photos") == {"original", "photo"}

    def test_stopwords_dropped(self):
        assert token_set("the photos must stay on my mac") == {
            "photo", "remain", "local",
        }


class TestSimilarity:
    def test_identical_phrases(self):
        assert phrase_similarity("original photos", "the original photos") == 1.0

    def test_disjoint_phrases(self):
        assert phrase_similarity("password", "photo") == 0.0

    def test_both_empty(self):
        assert phrase_similarity("", "") == 1.0

    def test_one_empty(self):
        assert phrase_similarity("photo", "") == 0.2

    def test_jaccard_and_overlap(self):
        assert jaccard({"a", "b"}, {"a", "b"}) == 1.0
        assert jaccard({"a"}, {"b"}) == 0.0
        assert overlap({"a"}, {"a", "b", "c"}) == 1.0


class TestAntonyms:
    def test_delete_preserve(self):
        assert relation_antonym("delete", "preserve") is True
        assert relation_antonym("preserve", "delete") is True

    def test_delete_remain(self):
        assert relation_antonym("delete", "remain") is True

    def test_unrelated(self):
        assert relation_antonym("delete", "upload") is False
        assert relation_antonym("", "delete") is False
