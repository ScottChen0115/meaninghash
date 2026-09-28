"""End-to-end tests: full pipeline and CLI on the photo-organizer demo."""
import json
from pathlib import Path

from typer.testing import CliRunner

from meaninghash.cli import app
from meaninghash.drift import DriftDetector
from meaninghash.extraction import SemanticExtractor
from meaninghash.models import DriftType
from meaninghash.providers.mock import MockProvider
from meaninghash.reporting import render_json, render_markdown

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "photo-organizer"

ORIGINAL = (EXAMPLES / "original.md").read_text()
CURRENT = (EXAMPLES / "current.md").read_text()

runner = CliRunner()


def audit_demo():
    extractor = SemanticExtractor(MockProvider())
    original = extractor.extract(ORIGINAL, source_id="original.md")
    current = extractor.extract(CURRENT, source_id="current.md")
    return original, current, DriftDetector().compare(original, current)


class TestFullPipeline:
    def test_demo_finds_expected_drift_types(self):
        _, _, report = audit_demo()
        types = {d.drift_type for d in report.drifts}
        assert DriftType.CONSTRAINT_WEAKENED in types  # must stay -> should stay
        assert DriftType.CONSTRAINT_REVERSAL in types  # never delete -> can remove
        assert DriftType.REQUIREMENT_DROPPED in types  # "may be moved" vanished
        assert DriftType.INTERNAL_CONFLICT not in types

    def test_demo_preserves_goal_and_preference(self):
        original, _, report = audit_demo()
        goal_ids = {r.id for r in original.goals}
        pref_ids = {r.id for r in original.preferences}
        preserved_originals = {oid for oid, _ in report.preserved_pairs}
        assert goal_ids <= preserved_originals
        assert pref_ids <= preserved_originals
        assert len(report.preserved_pairs) == 2

    def test_demo_scores_and_exit_code(self):
        _, _, report = audit_demo()
        assert 0.3 < report.integrity_score < 0.9
        assert report.exit_code("high") == 3
        assert report.total_original == 5
        assert report.total_current == 4

    def test_identical_documents_are_clean(self):
        extractor = SemanticExtractor(MockProvider())
        a = extractor.extract(ORIGINAL, source_id="a")
        b = extractor.extract(ORIGINAL, source_id="b")
        report = DriftDetector().compare(a, b)
        assert report.drifts == []
        assert report.integrity_score == 1.0
        assert report.exit_code("low") == 0


class TestRenderers:
    def test_markdown_report(self):
        original, current, report = audit_demo()
        md = render_markdown(report, original, current)
        assert md.startswith("# Semantic Drift Report")
        assert "CONSTRAINT REVERSAL" in md
        assert "Integrity Score" in md
        assert "Preserved Meaning" in md

    def test_json_report_roundtrip(self):
        original, current, report = audit_demo()
        data = json.loads(render_json(report, original, current))
        assert data["report"]["integrity_score"] == report.integrity_score
        assert len(data["original"]["goals"]) == 1
        assert data["current"]["constraints"]


class TestCli:
    def test_audit_json_exit_code(self):
        result = runner.invoke(
            app,
            ["audit", str(EXAMPLES / "original.md"), str(EXAMPLES / "current.md"),
             "--format", "json"],
        )
        assert result.exit_code == 3
        payload = json.loads(result.stdout)
        types = {d["drift_type"] for d in payload["report"]["drifts"]}
        assert "constraint_reversal" in types

    def test_audit_markdown_writes_output_file(self, tmp_path):
        out = tmp_path / "reports" / "drift.md"
        result = runner.invoke(
            app,
            ["audit", str(EXAMPLES / "original.md"), str(EXAMPLES / "current.md"),
             "--format", "markdown", "--output", str(out), "--quiet"],
        )
        assert result.exit_code == 3
        assert out.exists()
        assert "# Semantic Drift Report" in out.read_text()

    def test_audit_identical_files_pass(self):
        result = runner.invoke(
            app,
            ["audit", str(EXAMPLES / "original.md"), str(EXAMPLES / "original.md")],
        )
        assert result.exit_code == 0

    def test_extract_prints_contract(self):
        result = runner.invoke(app, ["extract", "Never delete the original photos."])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["constraints"][0]["canonical"]["relation"] == "delete"

    def test_audit_fail_on_never_exits_zero(self):
        result = runner.invoke(
            app,
            ["audit", str(EXAMPLES / "original.md"), str(EXAMPLES / "current.md"),
             "--fail-on", "never"],
        )
        assert result.exit_code == 0

    def test_min_integrity_flag(self):
        result = runner.invoke(
            app,
            ["audit", str(EXAMPLES / "original.md"), str(EXAMPLES / "current.md"),
             "--fail-on", "never", "--min-integrity", "0.99"],
        )
        assert result.exit_code == 2

    def test_unknown_provider_errors(self):
        result = runner.invoke(app, ["extract", "hello", "--provider", "nope"])
        assert result.exit_code == 4
