"""Tests for output layer: charts, reports, and export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import plotly.graph_objects as go

from aedm.analysis.demographics import analyze_all_disparities
from aedm.analysis.drift import detect_drift_cusum
from aedm.analysis.reskill import score_org_urgency
from aedm.output.charts import (
    demographic_disparity_bars,
    drift_sparklines,
    exposure_distribution,
    exposure_heatmap,
    urgency_matrix,
)
from aedm.output.export import export_csv, export_json, scores_to_dataframe
from aedm.output.report import (
    generate_html_report,
    generate_markdown_report,
    save_report,
)

if TYPE_CHECKING:
    from aedm.models.schemas import ExposureRate, ExposureScore, Role


# ── Charts ──────────────────────────────────────────────────────────────


class TestExposureHeatmap:
    def test_returns_plotly_figure(
        self, sample_roles: list[Role], sample_scores: list[ExposureScore]
    ) -> None:
        fig = exposure_heatmap(sample_roles, sample_scores)
        assert isinstance(fig, go.Figure)

    def test_has_traces(self, sample_roles: list[Role], sample_scores: list[ExposureScore]) -> None:
        fig = exposure_heatmap(sample_roles, sample_scores)
        assert len(fig.data) > 0

    def test_custom_title(
        self, sample_roles: list[Role], sample_scores: list[ExposureScore]
    ) -> None:
        fig = exposure_heatmap(sample_roles, sample_scores, title="Custom")
        assert fig.layout.title.text == "Custom"

    def test_metric_theoretical(
        self, sample_roles: list[Role], sample_scores: list[ExposureScore]
    ) -> None:
        fig = exposure_heatmap(sample_roles, sample_scores, metric="theoretical")
        assert isinstance(fig, go.Figure)
        assert fig.layout.xaxis.title.text == "Theoretical Exposure Score"

    def test_metric_observed(
        self, sample_roles: list[Role], sample_scores: list[ExposureScore]
    ) -> None:
        fig = exposure_heatmap(sample_roles, sample_scores, metric="observed")
        assert isinstance(fig, go.Figure)
        assert fig.layout.xaxis.title.text == "Observed Exposure Score"

    def test_metric_blended(
        self, sample_roles: list[Role], sample_scores: list[ExposureScore]
    ) -> None:
        fig = exposure_heatmap(sample_roles, sample_scores, metric="blended")
        assert isinstance(fig, go.Figure)
        assert fig.layout.xaxis.title.text == "Blended Exposure Score"


class TestDriftSparklines:
    def test_returns_plotly_figure(self) -> None:
        import numpy as np

        rng = np.random.default_rng(42)
        dr = detect_drift_cusum(
            [0.3, 0.35, 0.45, 0.55, 0.6],
            entity_id="Engineering",
            min_periods=3,
            n_permutations=50,
            rng=rng,
        )
        fig = drift_sparklines([dr])
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0


class TestDemographicDisparityBars:
    def test_returns_plotly_figure(
        self, sample_roles: list[Role], sample_scores: list[ExposureScore]
    ) -> None:
        segments = analyze_all_disparities(sample_roles, sample_scores)
        fig = demographic_disparity_bars(segments)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0


class TestUrgencyMatrix:
    def test_returns_plotly_figure(
        self,
        sample_roles: list[Role],
        sample_scores: list[ExposureScore],
        reference_rates: dict[str, ExposureRate],
    ) -> None:
        urgency = score_org_urgency(sample_roles, sample_scores, None, reference_rates)
        fig = urgency_matrix(sample_roles, sample_scores, urgency)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0


class TestExposureDistribution:
    def test_returns_plotly_figure(self, sample_scores: list[ExposureScore]) -> None:
        fig = exposure_distribution(sample_scores)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_empty_scores(self) -> None:
        fig = exposure_distribution([])
        assert isinstance(fig, go.Figure)


# ── Reports ─────────────────────────────────────────────────────────────


class TestMarkdownReport:
    def test_non_empty(self, sample_roles: list[Role], sample_scores: list[ExposureScore]) -> None:
        md = generate_markdown_report(
            sample_roles, sample_scores, org_mean=0.40, dept_means={"Engineering": 0.57}
        )
        assert len(md) > 0

    def test_contains_executive_summary(
        self, sample_roles: list[Role], sample_scores: list[ExposureScore]
    ) -> None:
        md = generate_markdown_report(
            sample_roles, sample_scores, org_mean=0.40, dept_means={"Engineering": 0.57}
        )
        assert "Executive Summary" in md

    def test_contains_department_section(
        self,
        sample_roles: list[Role],
        sample_scores: list[ExposureScore],
    ) -> None:
        md = generate_markdown_report(
            sample_roles,
            sample_scores,
            org_mean=0.40,
            dept_means={"Engineering": 0.57, "Finance": 0.50},
        )
        assert "Department Exposure" in md
        assert "Engineering" in md

    def test_with_urgency_and_demographics(
        self,
        sample_roles: list[Role],
        sample_scores: list[ExposureScore],
        reference_rates: dict[str, ExposureRate],
    ) -> None:
        urgency = score_org_urgency(sample_roles, sample_scores, None, reference_rates)
        segments = analyze_all_disparities(sample_roles, sample_scores)
        md = generate_markdown_report(
            sample_roles,
            sample_scores,
            org_mean=0.40,
            dept_means={"Engineering": 0.57},
            urgency_scores=urgency,
            demographic_segments=segments,
        )
        assert "Reskilling Urgency" in md
        assert "Demographic Disparity" in md

    def test_with_drift_results(
        self, sample_roles: list[Role], sample_scores: list[ExposureScore]
    ) -> None:
        import numpy as np

        rng = np.random.default_rng(42)
        dr = detect_drift_cusum(
            [0.3, 0.35, 0.45, 0.55, 0.6],
            entity_id="Engineering",
            min_periods=3,
            n_permutations=50,
            rng=rng,
        )
        md = generate_markdown_report(
            sample_roles,
            sample_scores,
            org_mean=0.40,
            dept_means={"Engineering": 0.57},
            drift_results=[dr],
        )
        assert "Drift Analysis" in md


class TestHtmlReport:
    def test_wraps_markdown(self) -> None:
        html = generate_html_report("# Hello World")
        assert "<!DOCTYPE html>" in html
        assert "Hello World" in html

    def test_includes_charts_section(self) -> None:
        html = generate_html_report("# Test", chart_htmls=["<div>chart1</div>"])
        assert "chart1" in html

    def test_inline_css(self) -> None:
        html = generate_html_report("# Test")
        assert "<style>" in html


class TestSaveReport:
    def test_creates_file(self, tmp_path: Path) -> None:
        out = tmp_path / "subdir" / "report.md"
        save_report("# Report content", out)
        assert out.exists()
        assert out.read_text() == "# Report content"


# ── Export ──────────────────────────────────────────────────────────────


class TestScoresToDataframe:
    def test_basic_columns(
        self, sample_roles: list[Role], sample_scores: list[ExposureScore]
    ) -> None:
        df = scores_to_dataframe(sample_roles, sample_scores)
        expected = {
            "role_id",
            "title",
            "department",
            "headcount",
            "soc_code",
            "soc_major_group",
            "theoretical_exposure",
            "observed_exposure",
            "blended_exposure",
            "exposure_tier",
        }
        assert expected.issubset(set(df.columns))
        assert len(df) == len(sample_scores)

    def test_with_urgency(
        self,
        sample_roles: list[Role],
        sample_scores: list[ExposureScore],
        reference_rates: dict[str, ExposureRate],
    ) -> None:
        urgency = score_org_urgency(sample_roles, sample_scores, None, reference_rates)
        df = scores_to_dataframe(sample_roles, sample_scores, urgency)
        assert "urgency_score" in df.columns
        assert "urgency_tier" in df.columns


class TestExportCsv:
    def test_creates_file(
        self,
        tmp_path: Path,
        sample_roles: list[Role],
        sample_scores: list[ExposureScore],
    ) -> None:
        out = tmp_path / "scores.csv"
        export_csv(sample_roles, sample_scores, out)
        assert out.exists()
        content = out.read_text()
        assert "role_id" in content
        assert "blended_exposure" in content

    def test_sorted_by_exposure(
        self,
        tmp_path: Path,
        sample_roles: list[Role],
        sample_scores: list[ExposureScore],
    ) -> None:
        import pandas as pd

        out = tmp_path / "scores.csv"
        export_csv(sample_roles, sample_scores, out)
        df = pd.read_csv(out)
        exposures = df["blended_exposure"].tolist()
        assert exposures == sorted(exposures, reverse=True)


class TestExportJson:
    def test_creates_valid_json(
        self,
        tmp_path: Path,
        sample_roles: list[Role],
        sample_scores: list[ExposureScore],
    ) -> None:
        out = tmp_path / "scores.json"
        export_json(
            sample_roles,
            sample_scores,
            out,
            org_mean=0.40,
            dept_means={"Engineering": 0.57},
        )
        assert out.exists()
        data = json.loads(out.read_text())
        assert "summary" in data
        assert "scores" in data

    def test_json_has_expected_keys(
        self,
        tmp_path: Path,
        sample_roles: list[Role],
        sample_scores: list[ExposureScore],
        reference_rates: dict[str, ExposureRate],
    ) -> None:
        urgency = score_org_urgency(sample_roles, sample_scores, None, reference_rates)
        segments = analyze_all_disparities(sample_roles, sample_scores)
        out = tmp_path / "full.json"
        export_json(
            sample_roles,
            sample_scores,
            out,
            urgency_scores=urgency,
            demographic_segments=segments,
            org_mean=0.40,
            dept_means={"Eng": 0.57},
        )
        data = json.loads(out.read_text())
        assert "summary" in data
        assert "scores" in data
        assert "urgency" in data
        assert "demographics" in data
        assert data["summary"]["total_roles"] == len(sample_roles)
