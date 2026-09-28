"""Canonicalization and normalization utilities (Stage 2 of the pipeline).

Maps surface words onto shared canonical tokens so that e.g.
"remove / delete / erase / destroy" all become `delete`, and
"cloud / remote server / third-party server" all become `cloud`.
"""
from __future__ import annotations

import re

# canonical token -> surface variants (matched after lowercasing +
# simple singularization). Multi-word concepts are handled token-wise.
SYNONYM_GROUPS: dict[str, set[str]] = {
    "delete": {"delete", "removes", "remove", "removed", "removing", "removal",
               "erase", "destroy", "eliminate", "discard", "purge", "deleted",
               "deleting", "erased"},
    "move": {"move", "relocate", "transfer", "moved", "moving", "transferred"},
    "upload": {"upload", "send", "transmit", "submit", "push", "sync",
               "uploaded", "uploading", "sent", "sending", "synced"},
    "store": {"store", "save", "cache", "persist", "stored", "saved", "saving"},
    "preserve": {"preserve", "retain", "preserved", "preserving", "retained"},
    "remain": {"remain", "stay", "keep", "reside", "stays", "stayed", "kept",
               "keeps", "remaining"},
    "process": {"process", "handle", "analyze", "scan", "compute", "index",
                "organize", "processed", "processing", "handled", "analyzed",
                "analyzing", "scanned", "scanning", "indexed", "indexing",
                "organizes", "organized"},
    "build": {"build", "create", "develop", "write", "implement", "generate",
              "make", "produce", "design", "built", "building", "created",
              "creating", "developing", "written", "implemented",
              "implementing", "generated", "generating", "designed"},
    "use": {"use", "utilize", "employ", "used", "using"},
    "run": {"run", "execute", "runs", "running", "executed", "executing"},
    "access": {"access", "read", "open", "accessed", "accessing", "reads",
               "reading", "opened", "opening"},
    "share": {"share", "disclose", "expose", "shared", "sharing", "shares"},
    "display": {"display", "show", "render", "displayed", "displaying",
                "shown", "showing", "rendered", "rendering", "shows"},
    "export": {"export", "convert", "exported", "exporting", "converted",
               "converting"},
    "copy": {"copy", "copied", "copying", "copies"},
    # subjects / nouns
    "photo": {"photo", "photos", "photograph", "image", "picture", "pictures"},
    "original": {"original", "originals", "source", "master"},
    "duplicate": {"duplicate", "duplicates", "dupe", "dupes"},
    "file": {"file", "files", "document", "documents"},
    "data": {"data", "information", "info"},
    "password": {"password", "passwords", "credential", "credentials", "secret", "secrets"},
    "metadata": {"metadata", "exif"},
    "video": {"video", "videos", "movie", "movies"},
    "music": {"music", "song", "songs"},
    "log": {"log", "logs", "telemetry"},
    "application": {"application", "app", "program", "tool", "software"},
    "language": {"language", "languages"},
    # objects / locations
    "local": {"local", "locally", "offline", "on-device", "on-device", "mac", "macos",
              "device", "computer", "machine", "on-premises"},
    "cloud": {"cloud", "remote", "server", "servers", "internet", "online", "external",
              "third-party"},
    "folder": {"folder", "folders", "directory", "directories"},
    "python": {"python"},
    "javascript": {"javascript", "js", "typescript", "ts"},
    "json": {"json"},
    "yaml": {"yaml", "yml"},
    "database": {"database", "db", "sqlite"},
    "browser": {"browser", "browsers"},
}

# Antonymous relations: flipping polarity while switching to the antonym
# preserves meaning ("never delete" == "must preserve").
ANTONYM_PAIRS: set[frozenset[str]] = {
    frozenset({"delete", "preserve"}),
    frozenset({"delete", "remain"}),
}

_WORD_MAP: dict[str, str] = {
    variant: canonical
    for canonical, variants in SYNONYM_GROUPS.items()
    for variant in variants
}

STOPWORDS = {
    "a", "an", "the", "is", "are", "be", "been", "being", "am", "was", "were",
    "will", "would", "shall", "must", "may", "might", "can", "could",
    "should", "to", "of", "on", "in", "at", "for", "with", "into", "from", "by",
    "and", "or", "not", "it", "its", "this", "that", "they", "them", "their",
    "has", "have", "had", "do", "does", "did", "done", "as", "if", "when",
    "after", "before", "while", "than", "then", "so", "we", "you", "i", "my",
    "your", "our", "user", "users", "s",
    "normally", "generally", "usually", "always", "never", "please",
    "successfully", "very", "more", "most", "whenever", "possible", "practical",
}

_SPLIT_RE = re.compile(r"[^a-z0-9]+")


def canonical_word(word: str) -> str | None:
    """Map a surface word to its canonical token (handles simple plurals)."""
    w = word.lower().strip().replace("'", "")
    if not w:
        return None
    if w in _WORD_MAP:
        return _WORD_MAP[w]
    if w.endswith("ies") and w[:-3] + "y" in _WORD_MAP:
        return _WORD_MAP[w[:-3] + "y"]
    if w.endswith("es") and w[:-2] in _WORD_MAP:
        return _WORD_MAP[w[:-2]]
    if w.endswith("s") and not w.endswith("ss") and w[:-1] in _WORD_MAP:
        return _WORD_MAP[w[:-1]]
    return w if w not in STOPWORDS else None


def token_set(text: str, drop_stopwords: bool = True) -> set[str]:
    """Canonicalized token set for a phrase (e.g. 'original_photos')."""
    tokens: set[str] = set()
    for part in _SPLIT_RE.split(text.lower().replace("'", "")):
        if not part:
            continue
        cw = canonical_word(part)
        if cw is None:
            continue
        if drop_stopwords and part in STOPWORDS:
            continue
        tokens.add(cw)
    return tokens


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def overlap(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def phrase_similarity(a: str, b: str) -> float:
    """Similarity of two phrases in canonical token space.

    Both empty -> 1.0 (aligned on "nothing"); one empty -> 0.2 mild penalty.
    """
    ta, tb = token_set(a), token_set(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.2
    return max(jaccard(ta, tb), overlap(ta, tb))


def relation_antonym(relation_a: str, relation_b: str) -> bool:
    ra, rb = token_set(relation_a), token_set(relation_b)
    for a in ra:
        for b in rb:
            if frozenset({a, b}) in ANTONYM_PAIRS:
                return True
    return False
