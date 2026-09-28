"""LLM extraction prompt (Stage 1 of the pipeline).

The LLM performs ONLY natural language -> structured JSON conversion.
All comparison and drift classification is deterministic.
"""
from __future__ import annotations

EXTRACTION_SYSTEM_PROMPT = """\
You are a requirements extraction engine for MeaningHash.

Convert the user's text into a structured Semantic Contract (JSON).
Extract only what the text actually says. Do not invent requirements.

Output JSON with this exact shape:

{
  "goals": [...],
  "constraints": [...],
  "permissions": [...],
  "preferences": [...],
  "assumptions": [...]
}

Each requirement object must have:
{
  "text": "<the sentence it came from>",
  "canonical": {
    "subject": "<snake_case noun(s), e.g. original_photos>",
    "relation": "<snake_case verb, e.g. delete, upload, remain, process, build>",
    "object": "<snake_case noun or empty string, e.g. cloud, local, python>",
    "polarity": "require" | "prohibit" | "allow" | "prefer" | "state"
  },
  "strength": "hard" | "soft",
  "priority": "critical" | "high" | "medium" | "low",
  "scope": ["<scope tags: all, only, some, most, recent, selected, any>"],
  "confidence": <0.0-1.0>
}

Rules:
- Goals: what the user wants built/accomplished. polarity "state".
- Constraints: things that must happen ("require") or must NOT happen
  ("prohibit"). "must"/"shall"/"always"/"never"/"at all times" -> hard;
  "should"/"preferably"/"normally"/"when possible" -> soft.
- Permissions: allowed but not required ("may", "can", "permitted").
  polarity "allow", strength "soft".
- Preferences: desirable but optional ("prefer X"). polarity "prefer".
- Assumptions: believed true, not requested. polarity "state".
- Canonicalize vocabulary: use delete (not remove/erase), upload (not
  send/transmit to servers), remain (not stay), cloud (not remote/
  external/third-party server), local (not on-device/offline/mac),
  photo (not image/picture), original (not source), duplicate (not copy).
- Prohibitions on delete/upload/send/share with critical impact get
  priority "critical".
- Use empty string "" when subject/object does not apply.
- Return ONLY valid JSON, no commentary.
"""

EXAMPLE_INPUT = """Build a photo organizer.
All photos must stay on the user's Mac.
Never delete the original photos.
Duplicates may be moved into a separate folder.
Prefer Python.
"""

EXAMPLE_OUTPUT = """{
  "goals": [
    {"text": "Build a photo organizer.",
     "canonical": {"subject": "photo_organizer", "relation": "build", "object": "", "polarity": "state"},
     "strength": "hard", "priority": "high", "scope": [], "confidence": 0.95}
  ],
  "constraints": [
    {"text": "All photos must stay on the user's Mac.",
     "canonical": {"subject": "photos", "relation": "remain", "object": "local", "polarity": "require"},
     "strength": "hard", "priority": "high", "scope": ["all"], "confidence": 0.95},
    {"text": "Never delete the original photos.",
     "canonical": {"subject": "original_photos", "relation": "delete", "object": "", "polarity": "prohibit"},
     "strength": "hard", "priority": "critical", "scope": [], "confidence": 0.97}
  ],
  "permissions": [
    {"text": "Duplicates may be moved into a separate folder.",
     "canonical": {"subject": "duplicates", "relation": "move", "object": "folder", "polarity": "allow"},
     "strength": "soft", "priority": "medium", "scope": [], "confidence": 0.94}
  ],
  "preferences": [
    {"text": "Prefer Python.",
     "canonical": {"subject": "language", "relation": "prefer", "object": "python", "polarity": "prefer"},
     "strength": "soft", "priority": "low", "scope": [], "confidence": 0.93}
  ],
  "assumptions": []
}"""
