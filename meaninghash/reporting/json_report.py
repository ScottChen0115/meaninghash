"""Machine-readable JSON drift report (plan Section 22)."""
from __future__ import annotations

import json

from meaninghash.models import DriftReport, SemanticContract


def build_report_dict(
    report: DriftReport,
    original: SemanticContract | None = None,
    current: SemanticContract | None = None,
) -> dict:
    """Full audit artifact: report + both contracts in grouped layout."""
    return {
        "report": report.model_dump(mode="json"),
        "original": original.to_grouped_dict() if original else None,
        "current": current.to_grouped_dict() if current else None,
    }


def render_json(
    report: DriftReport,
    original: SemanticContract | None = None,
    current: SemanticContract | None = None,
) -> str:
    return json.dumps(
        build_report_dict(report, original, current), indent=2, ensure_ascii=False
    )
