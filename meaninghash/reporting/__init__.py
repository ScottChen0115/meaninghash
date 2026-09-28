"""Report rendering: Markdown for humans, JSON for machines."""
from meaninghash.reporting.json_report import build_report_dict, render_json
from meaninghash.reporting.markdown import render_markdown, verdict_for

__all__ = ["build_report_dict", "render_json", "render_markdown", "verdict_for"]
