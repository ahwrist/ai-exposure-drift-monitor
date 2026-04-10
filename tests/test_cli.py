"""Tests for the Typer CLI interface."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from aedm.cli import app

runner = CliRunner()

SAMPLE_CSV = Path(__file__).parent.parent / "data" / "sample" / "acme_corp_roles.csv"
QUARTERLY_DIR = Path(__file__).parent.parent / "data" / "sample" / "acme_corp_quarterly"
REFERENCE_JSON = (
    Path(__file__).parent.parent / "data" / "reference" / "anthropic_exposure_rates.json"
)


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    """Provide a temporary output directory that is cleaned up after the test."""
    out = tmp_path / "cli_output"
    out.mkdir()
    return out


class TestVersion:
    def test_version_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "aedm v" in result.output

    def test_short_version_flag(self) -> None:
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "aedm v" in result.output


class TestAnalyze:
    def test_analyze_produces_output_files(self, tmp_output: Path) -> None:
        result = runner.invoke(
            app,
            [
                "analyze",
                "--input",
                str(SAMPLE_CSV),
                "--output",
                str(tmp_output),
                "--reference",
                str(REFERENCE_JSON),
            ],
        )
        assert result.exit_code == 0, result.output
        assert (tmp_output / "exposure_report.md").exists()
        assert (tmp_output / "exposure_report.html").exists()
        assert (tmp_output / "exposure_scores.csv").exists()
        assert (tmp_output / "exposure_scores.json").exists()

    def test_analyze_markdown_only(self, tmp_output: Path) -> None:
        result = runner.invoke(
            app,
            [
                "analyze",
                "--input",
                str(SAMPLE_CSV),
                "--output",
                str(tmp_output),
                "--reference",
                str(REFERENCE_JSON),
                "--format",
                "markdown",
            ],
        )
        assert result.exit_code == 0, result.output
        assert (tmp_output / "exposure_report.md").exists()
        # Other formats should not be produced
        assert not (tmp_output / "exposure_scores.csv").exists()

    def test_analyze_invalid_input(self, tmp_output: Path) -> None:
        result = runner.invoke(
            app,
            [
                "analyze",
                "--input",
                "/nonexistent/path.csv",
                "--output",
                str(tmp_output),
            ],
        )
        assert result.exit_code == 1
        # Should show human-readable error, not raw traceback
        assert "Error:" in result.output
        assert "Traceback" not in result.output


class TestDrift:
    def test_drift_runs_successfully(self, tmp_output: Path) -> None:
        result = runner.invoke(
            app,
            [
                "drift",
                "--input-dir",
                str(QUARTERLY_DIR),
                "--output",
                str(tmp_output),
                "--reference",
                str(REFERENCE_JSON),
            ],
        )
        assert result.exit_code == 0, result.output
        # Output should mention drift-related content
        assert "Drift" in result.output or "drift" in result.output.lower()

    def test_drift_invalid_dir(self, tmp_output: Path) -> None:
        result = runner.invoke(
            app,
            [
                "drift",
                "--input-dir",
                "/nonexistent/dir/",
                "--output",
                str(tmp_output),
            ],
        )
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Traceback" not in result.output


class TestReport:
    def test_report_delegates_to_analyze(self, tmp_output: Path) -> None:
        result = runner.invoke(
            app,
            [
                "report",
                "--input",
                str(SAMPLE_CSV),
                "--output",
                str(tmp_output),
                "--reference",
                str(REFERENCE_JSON),
            ],
        )
        assert result.exit_code == 0, result.output
        assert (tmp_output / "exposure_report.md").exists()
