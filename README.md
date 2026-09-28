# MeaningHash

**Semantic integrity & drift detection for evolving text.**

MeaningHash extracts a **Semantic Contract** — a structured snapshot of *what a
document means* (goals, constraints, permissions, preferences, assumptions) —
and diffs two versions of a document to answer one question:

> Has the current version drifted away from the original intent?

It is designed to run anywhere text evolves: prompts, specs, plans, agent
instructions, and generated artifacts. Deterministic by default (no API keys
needed), with optional LLM providers for richer extraction.

## Install

```bash
pip install -e ".[dev]"
pytest
```

## Usage

### Extract a Semantic Contract

```bash
# from a file
meaninghash extract --file spec.md

# from inline text, single-line JSON
meaninghash extract "Never delete the original photos." --compact
```

Output is grouped JSON (`goals` / `constraints` / `permissions` /
`preferences` / `assumptions`), each entry carrying a deterministic canonical
form (`subject | relation | object | polarity`), strength (hard/soft),
priority, and scope.

### Audit drift between two versions

```bash
meaninghash audit original.md current.md
meaninghash audit original.md current.md --format json -o drift-report.json
meaninghash audit original.md current.md --fail-on medium --min-integrity 0.9
```

Try the bundled demo:

```bash
meaninghash audit examples/photo-organizer/original.md examples/photo-organizer/current.md
```

The demo reports a **constraint reversal** ("Never delete the original
photos." → "Duplicates can be removed…"), a **weakened constraint**
(MUST → SHOULD), and a **dropped permission**, with a semantic integrity
score of `0.5985`.

## Drift taxonomy

| Drift | Meaning |
|---|---|
| `requirement_dropped` | An original requirement vanished from the current version |
| `constraint_reversal` | Prohibition became permission (or vice versa) |
| `constraint_weakened` / `constraint_strengthened` | MUST ↔ SHOULD |
| `scope_narrowed` / `scope_expanded` | all → some, every → any, … |
| `goal_changed` | The goal's object of work changed |
| `unsupported_addition` | New requirement with no counterpart in the original |
| `internal_conflict` | The current version contradicts itself |

Antonym flips that preserve meaning (e.g. "never delete" ≡ "must preserve")
are *not* flagged as reversals.

## Semantic integrity score

`1 − damage / total_weight`, where each requirement contributes a kind-based
weight (goal 10, constraint 8, permission 5, assumption 4, preference 2) and
each drift subtracts a severity-scaled fraction of the affected requirement's
weight (critical 1.0 / high 0.5 / medium 0.25 / low 0.1).

## CI exit codes

| Code | Condition |
|---|---|
| 0 | Meaning preserved |
| 1 | Warning-level drift |
| 2 | High-risk drift (also used for `--min-integrity` breaches) |
| 3 | Critical drift — intent is broken |
| 4 | Extraction error (provider failed after retries) |

`--fail-on {info,low,medium,high,critical,never}` sets the drift threshold;
`--min-integrity FLOAT` sets a floor on the integrity score.

## Providers

- `mock` (default) — fully deterministic rule-based extraction; ideal for
  tests, CI, and reproducible demos.
- `ollama` — local models via `--base-url` (default model `llama3.1`).
- `openai-compatible` — any OpenAI-style API (`--model`, `--base-url`; reads
  the key from `OPENAI_API_KEY`).

Invalid provider output triggers up to two feedback-guided retries before
the CLI exits with code 4.

## Project layout

```
meaninghash/
├── models/      # Requirement, SemanticContract, drift taxonomy, exit codes
├── extraction/  # normalization, rule-based parser, validating extractor
├── providers/   # mock / ollama / openai-compatible backends
├── matching/    # canonical-space similarity + greedy 1:1 alignment
├── drift/       # classification rules, severity mapping, detector
├── scoring/     # semantic integrity score
├── reporting/   # Markdown + JSON renderers
└── cli.py       # typer-based CLI (extract / audit)
```
