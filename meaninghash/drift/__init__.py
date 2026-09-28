"""Drift detection: taxonomy rules + the DriftDetector engine."""
from meaninghash.drift.detector import DriftDetector, detect_internal_conflicts
from meaninghash.drift.rules import (
    classify_added,
    classify_change,
    classify_dropped,
    scope_change,
)
from meaninghash.drift.severity import severity_for

__all__ = [
    "DriftDetector",
    "detect_internal_conflicts",
    "classify_added",
    "classify_change",
    "classify_dropped",
    "scope_change",
    "severity_for",
]
