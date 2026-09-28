"""MeaningHash: a semantic integrity protocol.

Detects intent drift between two versions of any text -- requirements docs,
prompts, agent plans, contracts -- by extracting a Semantic Contract from
each version and comparing them deterministically:

    extract -> normalize -> match -> classify drift -> score -> report

Only the extraction stage may use an LLM (pluggable provider); every
comparison decision is deterministic and reproducible.
"""
from meaninghash.drift import DriftDetector
from meaninghash.extraction import ExtractionError, SemanticExtractor
from meaninghash.matching import RequirementMatcher
from meaninghash.models import DriftReport, SemanticContract
from meaninghash.providers.mock import MockProvider
from meaninghash.scoring import compute_integrity

__version__ = "0.1.0"

__all__ = [
    "DriftDetector",
    "ExtractionError",
    "RequirementMatcher",
    "SemanticExtractor",
    "SemanticContract",
    "DriftReport",
    "MockProvider",
    "compute_integrity",
    "__version__",
]
