"""Human-readable Markdown drift report (plan Section 21)."""
from __future__ import annotations

from meaninghash.models import DriftReport, SemanticContract, Severity

_VERDICTS: dict[str, str] = {
    "none": "PRESERVED — meaning is intact; no semantic drift detected.",
    Severity.INFO.value: "PRESERVED — only informational notes.",
    Severity.LOW.value: "MINOR DRIFT — cosmetic or low-impact changes.",
    Severity.MEDIUM.value: "WARNING — meaningful drift needs review.",
    Severity.HIGH.value: "HIGH RISK — important meaning has changed.",
    Severity.CRITICAL.value: "CRITICAL — meaning has been broken; "
    "the current version violates the original intent.",
}


def _snippet(text: str | None, limit: int = 100) -> str:
    if not text:
        return "(none)"
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def verdict_for(report: DriftReport) -> str:
    worst = report.max_severity()
    return _VERDICTS["none" if worst is None else worst.value]


def render_markdown(
    report: DriftReport,
    original: SemanticContract | None = None,
    current: SemanticContract | None = None,
) -> str:
    lines: list[str] = ["# Semantic Drift Report", ""]

    counts = report.counts_by_severity()
    lines += [
        f"- **Original:** {report.original_source} — {report.total_original} requirements",
        f"- **Current:** {report.current_source} — {report.total_current} requirements",
        f"- **Matched:** {report.matched} / preserved {len(report.preserved_pairs)}",
        f"- **Drifts:** {len(report.drifts)} "
        f"(critical: {counts.get('critical', 0)}, high: {counts.get('high', 0)}, "
        f"medium: {counts.get('medium', 0)}, low: {counts.get('low', 0)})",
        f"- **Semantic Integrity Score:** `{report.integrity_score:.4f} / 1.000`",
        "",
        f"> **{verdict_for(report)}**",
        "",
    ]

    order = [
        Severity.CRITICAL,
        Severity.HIGH,
        Severity.MEDIUM,
        Severity.LOW,
        Severity.INFO,
    ]
    if report.drifts:
        lines += ["## Drift", ""]
        n = 0
        for level in order:
            for drift in report.drifts:
                if drift.severity != level:
                    continue
                n += 1
                lines.append(f"### {n}. {drift.label} — {level.value.upper()}")
                if drift.transformation:
                    lines.append(f"- **Transformation:** `{drift.transformation}`")
                ids = " / ".join(
                    x for x in (drift.original_requirement_id, drift.current_requirement_id) if x
                )
                if ids:
                    lines.append(f"- **Requirements:** {ids}")
                lines.append(f"- **Confidence:** {drift.confidence:.2f}")
                if drift.explanation:
                    lines.append(f"- **Why:** {drift.explanation}")
                lines.append(f"- **Original:** {_snippet(drift.evidence_original)}")
                lines.append(f"- **Current:** {_snippet(drift.evidence_current)}")
                lines.append("")
    else:
        lines += ["## Drift", "", "None — every requirement's meaning is preserved.", ""]

    if report.preserved_pairs:
        lines += ["## Preserved Meaning", ""]
        for orig_id, cur_id in report.preserved_pairs:
            o = original.get(orig_id) if original else None
            c = current.get(cur_id) if current else None
            lines.append(
                f"- `{orig_id}` ↔ `{cur_id}` — "
                f"{_snippet((o.text if o else None), 80)}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
