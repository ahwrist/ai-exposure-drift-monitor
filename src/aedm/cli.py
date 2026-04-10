"""Typer-based CLI entrypoint for AEDM."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.table import Table

from aedm import __version__

if TYPE_CHECKING:
    from aedm.models.schemas import ExposureScore, Role

app = typer.Typer(
    name="aedm",
    help="AI Exposure Drift Monitor — Measure, track, and act on AI workforce exposure.",
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"aedm v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            callback=_version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
) -> None:
    """AI Exposure Drift Monitor."""


@app.command()
def analyze(
    input: Annotated[Path, typer.Option("--input", "-i", help="Path to roles CSV file.")],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Output directory for reports.")
    ] = Path("report"),
    reference: Annotated[
        Path,
        typer.Option("--reference", "-r", help="Path to reference exposure rates JSON."),
    ] = Path("data/reference/anthropic_exposure_rates.json"),
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: markdown, html, csv, json, or all.",
        ),
    ] = "all",
) -> None:
    """Analyze AI exposure for an organization's roles."""
    try:
        from aedm.analysis.demographics import analyze_all_disparities
        from aedm.analysis.exposure import (
            compute_org_exposure,
            exposure_by_department,
            org_mean_exposure,
        )
        from aedm.analysis.reskill import score_org_urgency
        from aedm.ingest.parser import load_reference_rates, parse_csv
        from aedm.output.export import export_csv, export_json
        from aedm.output.report import (
            generate_html_report,
            generate_markdown_report,
            save_report,
        )

        console.print(f"\n[bold]AEDM v{__version__}[/bold] — AI Exposure Analysis\n")

        # Load data
        with console.status("Loading data..."):
            roles = parse_csv(input)
            rates = load_reference_rates(reference)

        console.print(f"  Loaded [cyan]{len(roles)}[/cyan] roles from {input}")

        # Compute exposure
        with console.status("Computing exposure indices..."):
            scores = compute_org_exposure(roles, rates)
            mean_exp = org_mean_exposure(roles, scores)
            dept_exp = exposure_by_department(roles, scores)

        # Urgency scoring
        with console.status("Scoring reskilling urgency..."):
            urgency = score_org_urgency(roles, scores, None, rates)

        # Demographics
        with console.status("Analyzing demographic disparities..."):
            segments = analyze_all_disparities(roles, scores)

        # Summary table
        _print_summary(roles, scores, mean_exp, dept_exp)

        # Generate outputs
        output.mkdir(parents=True, exist_ok=True)

        if format in ("markdown", "all"):
            md = generate_markdown_report(roles, scores, mean_exp, dept_exp, urgency, segments)
            save_report(md, output / "exposure_report.md")

        if format in ("html", "all"):
            md = generate_markdown_report(roles, scores, mean_exp, dept_exp, urgency, segments)
            html = generate_html_report(md)
            save_report(html, output / "exposure_report.html")

        if format in ("csv", "all"):
            export_csv(roles, scores, output / "exposure_scores.csv", urgency)

        if format in ("json", "all"):
            export_json(
                roles,
                scores,
                output / "exposure_scores.json",
                urgency,
                segments,
                org_mean=mean_exp,
                dept_means=dept_exp,
            )

        console.print(f"\n  Reports saved to [green]{output}/[/green]")
        console.print()

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}\n")
        raise typer.Exit(code=1) from None


@app.command()
def drift(
    input_dir: Annotated[
        Path,
        typer.Option(
            "--input-dir",
            "-d",
            help="Directory containing quarterly CSV snapshots.",
        ),
    ],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory.")] = Path(
        "report"
    ),
    reference: Annotated[
        Path,
        typer.Option("--reference", "-r", help="Path to reference exposure rates JSON."),
    ] = Path("data/reference/anthropic_exposure_rates.json"),
) -> None:
    """Detect exposure drift across multiple time periods."""
    try:
        from aedm.analysis.drift import detect_org_drift
        from aedm.analysis.exposure import compute_org_exposure, exposure_by_department
        from aedm.ingest.parser import load_quarterly_snapshots, load_reference_rates

        console.print(f"\n[bold]AEDM v{__version__}[/bold] — Drift Analysis\n")

        with console.status("Loading snapshots..."):
            snapshots = load_quarterly_snapshots(input_dir)
            rates = load_reference_rates(reference)

        console.print(f"  Loaded [cyan]{len(snapshots)}[/cyan] snapshots from {input_dir}")

        # Compute exposure for each snapshot and build time series by department
        dept_series: dict[str, list[float]] = {}
        for snapshot in snapshots:
            scores = compute_org_exposure(snapshot.roles, rates)
            dept_exp = exposure_by_department(snapshot.roles, scores)
            for dept, mean in dept_exp.items():
                if dept not in dept_series:
                    dept_series[dept] = []
                dept_series[dept].append(mean)

        # Detect drift
        with console.status("Running drift detection..."):
            drift_results = detect_org_drift(dept_series)

        # Print results
        table = Table(title="Drift Analysis Results")
        table.add_column("Department", style="cyan")
        table.add_column("Direction")
        table.add_column("Slope", justify="right")
        table.add_column("p-value", justify="right")
        table.add_column("Periods", justify="right")

        for dr in sorted(drift_results, key=lambda d: abs(d.trend_slope), reverse=True):
            direction_style = {
                "Accelerating": "[red]Accelerating[/red]",
                "Stable": "[dim]Stable[/dim]",
                "Decelerating": "[green]Decelerating[/green]",
            }
            table.add_row(
                dr.entity_id,
                direction_style.get(dr.direction.value, dr.direction.value),
                f"{dr.trend_slope:+.4f}",
                f"{dr.p_value:.3f}",
                str(dr.n_periods),
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}\n")
        raise typer.Exit(code=1) from None


@app.command()
def report(
    input: Annotated[Path, typer.Option("--input", "-i", help="Path to roles CSV file.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory.")] = Path(
        "report"
    ),
    format: Annotated[str, typer.Option("--format", "-f", help="Output format.")] = "all",
    reference: Annotated[
        Path,
        typer.Option("--reference", "-r", help="Path to reference exposure rates JSON."),
    ] = Path("data/reference/anthropic_exposure_rates.json"),
) -> None:
    """Generate exposure analysis reports."""
    # Delegate to analyze with report focus
    analyze(input=input, output=output, reference=reference, format=format)


@app.command()
def dashboard(
    input: Annotated[
        Path,
        typer.Option("--input", "-i", help="Path to roles CSV file."),
    ] = Path("data/sample/acme_corp_roles.csv"),
    reference: Annotated[
        Path,
        typer.Option("--reference", "-r", help="Path to reference exposure rates JSON."),
    ] = Path("data/reference/anthropic_exposure_rates.json"),
    port: Annotated[int, typer.Option("--port", "-p", help="Dashboard port.")] = 8501,
) -> None:
    """Launch the interactive Streamlit dashboard."""
    import subprocess
    import sys

    dashboard_path = Path(__file__).parent / "dashboard" / "app.py"

    console.print(f"\n[bold]AEDM v{__version__}[/bold] — Launching Dashboard\n")
    console.print(f"  Data: {input}")
    console.print(f"  Dashboard: http://localhost:{port}")
    console.print()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(dashboard_path),
            "--server.port",
            str(port),
            "--",
            str(input),
            str(reference),
        ],
        check=False,
    )


def _print_summary(
    roles: list[Role],
    scores: list[ExposureScore],
    mean_exp: float,
    dept_exp: dict[str, float],
) -> None:
    """Print a summary table to the console."""
    from aedm.models.enums import ExposureTier

    total_hc = sum(r.headcount for r in roles)

    console.print(f"  Org mean exposure: [bold]{mean_exp:.1%}[/bold]")
    console.print(f"  Total headcount:   [bold]{total_hc:,}[/bold]")
    console.print()

    # Department table
    table = Table(title="Exposure by Department")
    table.add_column("Department", style="cyan")
    table.add_column("Mean Exposure", justify="right")
    table.add_column("Tier")

    for dept, mean in sorted(dept_exp.items(), key=lambda x: -x[1]):
        tier = ExposureTier.from_score(mean)
        tier_style = {
            "Critical": "[red]Critical[/red]",
            "High": "[yellow]High[/yellow]",
            "Moderate": "[cyan]Moderate[/cyan]",
            "Low": "[green]Low[/green]",
        }
        table.add_row(dept, f"{mean:.1%}", tier_style.get(tier.value, tier.value))

    console.print(table)
