"""MeaningHash command-line interface (plan Sections 23-24).

Commands:
    meaninghash extract  "text..."     # text -> Semantic Contract JSON
    meaninghash audit orig.md cur.md   # full drift audit with CI exit codes

Exit codes: 0 = OK, 1 = warning drift, 2 = high-risk, 3 = critical,
4 = extraction error.
"""
from __future__ import annotations

import json as jsonlib
from pathlib import Path
from typing import Optional

import typer

from meaninghash.config import Settings
from meaninghash.drift import DriftDetector
from meaninghash.extraction import ExtractionError, SemanticExtractor
from meaninghash.providers import create_provider
from meaninghash.reporting import render_json, render_markdown, verdict_for

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="MeaningHash — semantic integrity & drift detection for evolving text.",
)
_FAIL_ON_VALUES = ("info", "low", "medium", "high", "critical", "never", "none")


def _settings(model: str | None, base_url: str | None) -> Settings:
    return Settings(model=model, base_url=base_url)


def _read_text(text: str | None, file: Path | None) -> str:
    if file is not None:
        return file.read_text(encoding="utf-8")
    if text:
        return text
    raise typer.BadParameter("provide TEXT or --file")


@app.command()
def extract(
    text: Optional[str] = typer.Argument(
        None, help="Text to extract from (or use --file)."
    ),
    file: Optional[Path] = typer.Option(
        None, "--file", "-f", exists=True, dir_okay=False, readable=True,
        help="Read input from a file instead of TEXT.",
    ),
    provider: str = typer.Option(
        "mock", "--provider", "-p", help="mock | ollama | openai-compatible"
    ),
    model: Optional[str] = typer.Option(None, "--model", help="Provider model name."),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Provider base URL."),
    compact: bool = typer.Option(False, "--compact", help="Single-line JSON output."),
) -> None:
    """Extract a Semantic Contract from text and print it as JSON."""
    source = _read_text(text, file)
    try:
        extractor = SemanticExtractor(
            create_provider(provider, _settings(model, base_url))
        )
        contract = extractor.extract(
            source,
            source_type="document",
            source_id=file.name if file else "inline",
            path=str(file.resolve()) if file else None,
        )
    except (ExtractionError, ValueError) as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=4) from exc
    payload = jsonlib.dumps(
        contract.to_grouped_dict(), ensure_ascii=False, indent=None if compact else 2
    )
    typer.echo(payload)


@app.command()
def audit(
    original: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="Original document."
    ),
    current: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True,
        help="Current (suspect) document.",
    ),
    provider: str = typer.Option("mock", "--provider", "-p"),
    model: Optional[str] = typer.Option(None, "--model"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    fmt: str = typer.Option("markdown", "--format", help="markdown | json"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Also write the report to this file."
    ),
    fail_on: str = typer.Option(
        "high", "--fail-on",
        help="Exit non-zero when drift reaches this severity: "
        + "|".join(_FAIL_ON_VALUES),
    ),
    min_integrity: Optional[float] = typer.Option(
        None, "--min-integrity", min=0.0, max=1.0,
        help="Also fail when the integrity score drops below this.",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress the rendered report on stdout."
    ),
) -> None:
    """Audit semantic drift between two documents (CI-friendly exit codes)."""
    if fmt not in ("markdown", "json"):
        raise typer.BadParameter(f"--format must be markdown or json, got {fmt!r}")
    if fail_on not in _FAIL_ON_VALUES:
        raise typer.BadParameter(
            f"--fail-on must be one of {', '.join(_FAIL_ON_VALUES)}"
        )

    settings = _settings(model, base_url)
    try:
        extractor = SemanticExtractor(create_provider(provider, settings))
        orig_contract = extractor.extract(
            original.read_text(encoding="utf-8"),
            source_type="document",
            source_id=original.name,
            path=str(original.resolve()),
        )
        cur_contract = extractor.extract(
            current.read_text(encoding="utf-8"),
            source_type="document",
            source_id=current.name,
            path=str(current.resolve()),
        )
    except (ExtractionError, ValueError) as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=4) from exc

    report = DriftDetector().compare(orig_contract, cur_contract)
    rendered = (
        render_json(report, orig_contract, cur_contract)
        if fmt == "json"
        else render_markdown(report, orig_contract, cur_contract)
    )
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    if not quiet:
        typer.echo(rendered)

    code = report.exit_code(fail_on)
    if min_integrity is not None and report.integrity_score < min_integrity:
        code = max(code, 2)
        typer.secho(
            f"integrity {report.integrity_score:.4f} is below the minimum "
            f"{min_integrity:.4f}",
            fg=typer.colors.RED,
            err=True,
        )
    typer.secho(
        f"{verdict_for(report)}  (integrity {report.integrity_score:.4f}, exit {code})",
        fg=(
            typer.colors.RED if code >= 2
            else typer.colors.YELLOW if code == 1
            else typer.colors.GREEN
        ),
        err=True,
    )
    raise typer.Exit(code=code)


def main() -> None:
    app()


if __name__ == "__main__":
    main()

