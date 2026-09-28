"""Deterministic, dictionary-driven extraction (the "mock provider" brain).

Converts natural language into a raw Semantic Contract dict using regex
modality detection + canonicalization dictionaries. Intentionally simple
and fully deterministic so that:

- tests and CI run without any API keys,
- the photo-organizer demo reproduces exactly,
- the same logic seeds the benchmark baseline.

Production-quality extraction uses the LLM providers (see providers/).
"""
from __future__ import annotations

import re

from meaninghash.extraction import normalization as norm

# --- modality patterns (checked in this order) ---------------------------
PROHIBIT_PATTERNS = [
    r"\bnever\b", r"\bmust not\b", r"\bmustn'?t\b", r"\bdo not\b",
    r"\bdon'?t\b", r"\bshall not\b", r"\bforbidden\b", r"\bmay not\b",
    r"\bcannot\b", r"\bcan'?t\b", r"\bis not allowed\b",
    r"\bare not allowed\b",
]
REQUIRE_HARD_PATTERNS = [
    r"\bmust\b", r"\bshall\b", r"\bis required\b", r"\bare required\b",
    r"\brequired to\b", r"\bhas to\b", r"\bneeds to\b", r"\bat all times\b",
    r"\balways\b",
]
REQUIRE_SOFT_PATTERNS = [r"\bshould\b", r"\bsupposed to\b"]
SOFTENER_PATTERNS = [
    r"\bnormally\b", r"\bpreferably\b", r"\bpreferred\b", r"\bwhen possible\b",
    r"\bwhenever practical\b", r"\bwhen practical\b", r"\bgenerally\b",
    r"\busually\b", r"\bif possible\b", r"\bas much as possible\b",
    r"\bwhere practical\b",
]
ALLOW_PATTERNS = [
    r"\bmay\b", r"\bis allowed\b", r"\bare allowed\b", r"\bpermitted\b",
    r"\bit is permitted\b", r"\bcan\b", r"\bcould\b",
]
PREFER_PATTERNS = [r"\bprefer\w*\b"]
ASSUMPTION_PATTERNS = [r"\bassum\w+\b", r"\bhas at least\b", r"\balready\b",
                       r"\bis expected to\b"]

RELATION_TOKENS = {
    "delete", "move", "upload", "store", "preserve", "remain", "process",
    "build", "use", "run", "access", "share", "display", "export", "copy",
    "prefer",
}

_GOAL_VERBS = {"build", "create", "develop", "write", "implement", "generate",
               "make", "produce", "design", "organize"}

_LANGUAGES = {"python", "javascript", "java", "rust", "go", "typescript",
              "c", "cpp"}

_DANGEROUS_RELATIONS = {"delete", "upload", "send", "share", "transmit"}

OBJECT_TOKENS = {"local", "cloud", "folder", "python", "javascript", "json",
                 "yaml", "database", "browser", "device"}

NOUN_TOKENS = {"photo", "original", "duplicate", "file", "data", "password",
               "metadata", "video", "music", "log", "application", "organizer",
               "player", "report", "reports", "key", "token", "image",
               "language"}

_SCOPE_TAGS = {
    "all": "all", "every": "all", "any": "any", "only": "only", "some": "some",
    "most": "most", "recent": "recent", "recently": "recent", "new": "recent",
    "old": "recent", "selected": "selected",
}
# Broadness rank used for scope narrowing/expansion decisions.
SCOPE_BROADNESS = {"all": 3, "every": 3, "most": 2, "some": 1, "any": 1,
                   "only": 1, "selected": 1, "recent": 1}


def _matches(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def _extend_prose(out: list[str], joined: str) -> None:
    """Append sentence-split prose (stripping any leading list marker)."""
    joined = _BULLET_RE.sub("", joined.strip(), count=1)
    if not joined:
        return
    out.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+", joined) if s.strip())


def split_sentences(text: str) -> list[str]:
    """Split on paragraphs first (joining wrapped lines), then sentences.

    Bullet/list lines are kept as individual units so that each bullet
    becomes exactly one requirement.
    """
    sentences: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        lines = [ln.strip() for ln in paragraph.splitlines() if ln.strip()]
        prose_run: list[str] = []
        for line in lines:
            if _BULLET_RE.match(line):
                if prose_run:
                    _extend_prose(sentences, " ".join(prose_run))
                    prose_run = []
                bullet = _BULLET_RE.sub("", line).strip()
                if bullet:
                    sentences.append(bullet)
            else:
                prose_run.append(line)
        if prose_run:
            _extend_prose(sentences, " ".join(prose_run))
    return sentences


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower().replace("'", ""))
            if t]


def _find_relation(tokens: list[str]) -> tuple[str, int] | None:
    """First relation verb in the sentence (canonical form + position)."""
    for i, tok in enumerate(tokens):
        cw = norm.canonical_word(tok)
        if cw in RELATION_TOKENS:
            return cw, i
    return None


def _subject_after(tokens: list[str], start: int) -> str:
    """Subject-ish canonical tokens after a verb (imperative sentences)."""
    out: list[str] = []
    for tok in tokens[start + 1:]:
        if tok in {"after", "before", "when", "if", "while"}:
            break
        cw = norm.canonical_word(tok)
        if cw in NOUN_TOKENS:
            out.append(cw)
        if len(out) >= 2:
            break
    return "_".join(dict.fromkeys(out))


_GROUP_OF = {
    "goal": "goals",
    "constraint": "constraints",
    "permission": "permissions",
    "preference": "preferences",
    "assumption": "assumptions",
}


def analyze_sentence(sentence: str) -> dict | None:
    """Classify one sentence into a raw requirement dict (None to skip)."""
    low = sentence.lower()
    tokens = _tokens(low)

    scope: list[str] = []
    for tok in tokens:
        tag = _SCOPE_TAGS.get(tok)
        if tag and tag not in scope:
            scope.append(tag)

    found = _find_relation(tokens)
    relation, rel_idx = found if found else ("", -1)
    imperative = rel_idx == 0

    if tokens and tokens[0] in _GOAL_VERBS and not _matches(PROHIBIT_PATTERNS, low):
        kind, polarity, strength = "goal", "state", "hard"
    elif _matches(ASSUMPTION_PATTERNS, low):
        kind, polarity, strength = "assumption", "state", "soft"
    elif _matches(PREFER_PATTERNS, low):
        kind, polarity, strength = "preference", "prefer", "soft"
    elif _matches(PROHIBIT_PATTERNS, low):
        kind, polarity, strength = "constraint", "prohibit", "hard"
    elif _matches(REQUIRE_HARD_PATTERNS, low):
        kind, polarity, strength = "constraint", "require", "hard"
        if _matches(SOFTENER_PATTERNS, low):
            strength = "soft"
    elif _matches(REQUIRE_SOFT_PATTERNS, low) or _matches(SOFTENER_PATTERNS, low):
        kind, polarity, strength = "constraint", "require", "soft"
    elif _matches(ALLOW_PATTERNS, low):
        kind, polarity, strength = "permission", "allow", "soft"
    elif imperative:
        kind, polarity, strength = "constraint", "require", "hard"
    else:
        return None

    subject = ""
    if rel_idx > 0:
        before = [norm.canonical_word(t) for t in tokens[:rel_idx]]
        subject = "_".join(dict.fromkeys(b for b in before if b in NOUN_TOKENS))
        if not subject:
            subject = _subject_after(tokens, rel_idx)
    elif rel_idx == 0:
        subject = _subject_after(tokens, rel_idx)

    object_ = ""
    if rel_idx >= 0:
        for tok in tokens[rel_idx + 1:]:
            cw = norm.canonical_word(tok)
            if cw in OBJECT_TOKENS:
                object_ = cw
                break
    if not object_:
        for tok in tokens:
            cw = norm.canonical_word(tok)
            if cw in OBJECT_TOKENS:
                object_ = cw
                break

    # "Prefer Python." / "Python must be used." -> the language is the subject
    if not subject and object_ in _LANGUAGES:
        subject = "language"

    if kind == "goal":
        priority = "critical"
    elif polarity == "prohibit":
        priority = "high"
    elif relation in _DANGEROUS_RELATIONS and strength == "hard":
        priority = "high"
    elif strength == "hard":
        priority = "medium"
    else:
        priority = "low"

    return {
        "kind": kind,
        "text": sentence,
        "canonical": {
            "subject": subject,
            "relation": relation,
            "object": object_,
            "polarity": polarity,
        },
        "strength": strength,
        "priority": priority,
        "scope": scope,
        "confidence": 0.7,
    }


def parse_text(text: str) -> dict:
    """Deterministic NL -> raw Semantic Contract dict (grouped format)."""
    contract: dict[str, list[dict]] = {
        "goals": [],
        "constraints": [],
        "permissions": [],
        "preferences": [],
        "assumptions": [],
    }
    for sentence in split_sentences(text):
        parsed = analyze_sentence(sentence)
        if parsed is None:
            continue
        contract[_GROUP_OF[parsed.pop("kind")]].append(parsed)
    return contract

