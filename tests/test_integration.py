"""End-to-end integration tests for the full AEDM pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from aedm.analysis.demographics import analyze_all_disparities
from aedm.analysis.drift import detect_org_drift
from aedm.analysis.exposure import (
    compute_org_exposure,
    exposure_by_department,
    org_mean_exposure,
)
from aedm.analysis.reskill import score_org_urgency
from aedm.ingest.parser import (
    load_quarterly_snapshots,
    load_reference_rates,
    parse_csv,
)
from aedm.output.export import export_csv, export_json
from aedm.output.report import generate_html_report, generate_markdown_report

SAMPLE_CSV = Path(__file__).parent.parent / "data" / "sample" / "acme_corp_roles.csv"
QUARTERLY_DIR = Path(__file__).parent.parent / "data" / "sample" / "acme_corp_quarterly"
REFERENCE_PATH = (
    Path(__file__).parent.parent / "data" / "reference" / "anthropic_exposure_rates.json"
)


class TestFullPipeline:
    """End-to-end: CSV -> exposure -> drift -> demographics -> urgency -> report -> export."""

    def test_full_pipeline_produces_consistent_results(self, tmp_path: Path) -> None:
        # 1. Ingest
        roles = parse_csv(SAMPLE_CSV)
        rates = load_reference_rates(REFERENCE_PATH)
        assert len(roles) > 0
        assert len(rates) > 0

        # 2. Exposure
        scores = compute_org_exposure(roles, rates)
        assert len(scores) == len(roles)
        mean_exp = org_mean_exposure(roles, scores)
        assert 0.0 < mean_exp < 1.0
        dept_exp = exposure_by_department(roles, scores)
        assert len(dept_exp) > 0
        assert all(0.0 <= v <= 1.0 for v in dept_exp.values())

        # 3. Demographics
        segments = analyze_all_disparities(roles, scores)
        assert len(segments) > 0
        for seg in segments:
            assert seg.headcount > 0
            assert seg.mean_exposure >= 0.0

        # 4. Urgency
        urgency = score_org_urgency(roles, scores, None, rates)
        assert len(urgency) == len(roles)
        assert all(0.0 <= u.score <= 1.0 for u in urgency)

        # 5. Report
        md = generate_markdown_report(roles, scores, mean_exp, dept_exp, urgency, segments)
        assert len(md) > 100
        assert "Executive Summary" in md

        html = generate_html_report(md)
        assert "<!DOCTYPE html>" in html
        assert len(html) > len(md)

        # 6. Export
        csv_path = tmp_path / "scores.csv"
        export_csv(roles, scores, csv_path, urgency)
        assert csv_path.exists()
        assert csv_path.stat().st_size > 0

        json_path = tmp_path / "scores.json"
        export_json(
            roles,
            scores,
            json_path,
            urgency_scores=urgency,
            demographic_segments=segments,
            org_mean=mean_exp,
            dept_means=dept_exp,
        )
        assert json_path.exists()

        # 7. Verify JSON structure
        data = json.loads(json_path.read_text())
        assert data["summary"]["total_roles"] == len(roles)
        assert data["summary"]["total_headcount"] > 0
        assert abs(data["summary"]["org_mean_exposure"] - round(mean_exp, 4)) < 1e-6
        assert "scores" in data
        assert len(data["scores"]) == len(roles)
        assert "urgency" in data
        assert "demographics" in data

        # Verify each score entry has the required keys
        score_keys = {
            "role_id",
            "title",
            "department",
            "headcount",
            "theoretical",
            "observed",
            "blended",
            "tier",
            "soc_major_group",
        }
        for entry in data["scores"]:
            assert score_keys.issubset(set(entry.keys()))


class TestDriftPipeline:
    """End-to-end drift pipeline using quarterly snapshots."""

    def test_quarterly_drift_detection(self) -> None:
        snapshots = load_quarterly_snapshots(QUARTERLY_DIR)
        rates = load_reference_rates(REFERENCE_PATH)
        assert len(snapshots) >= 2

        # Build department time series
        dept_series: dict[str, list[float]] = {}
        for snapshot in snapshots:
            scores = compute_org_exposure(snapshot.roles, rates)
            dept_exp = exposure_by_department(snapshot.roles, scores)
            for dept, mean in dept_exp.items():
                if dept not in dept_series:
                    dept_series[dept] = []
                dept_series[dept].append(mean)

        # Detect drift (only on departments with enough periods)
        min_periods = min(len(v) for v in dept_series.values())
        if min_periods >= 3:
            drift_results = detect_org_drift(dept_series, min_periods=3, n_permutations=50)
            assert len(drift_results) > 0
            for dr in drift_results:
                assert dr.n_periods >= 3
                assert 0.0 <= dr.p_value <= 1.0

    def test_drift_feeds_into_report(self, tmp_path: Path) -> None:
        import numpy as np

        from aedm.analysis.drift import detect_drift_cusum

        roles = parse_csv(SAMPLE_CSV)
        rates = load_reference_rates(REFERENCE_PATH)
        scores = compute_org_exposure(roles, rates)
        dept_exp = exposure_by_department(roles, scores)
        mean_exp = org_mean_exposure(roles, scores)

        # Simulate drift for one department
        rng = np.random.default_rng(42)
        dr = detect_drift_cusum(
            [0.3, 0.35, 0.45, 0.55, 0.6],
            entity_id="Engineering",
            min_periods=3,
            n_permutations=50,
            rng=rng,
        )

        md = generate_markdown_report(roles, scores, mean_exp, dept_exp, drift_results=[dr])
        assert "Drift Analysis" in md
        assert "Engineering" in md

        # Export with drift
        json_path = tmp_path / "full.json"
        export_json(
            roles,
            scores,
            json_path,
            drift_results=[dr],
            org_mean=mean_exp,
            dept_means=dept_exp,
        )
        data = json.loads(json_path.read_text())
        assert "drift" in data
        assert len(data["drift"]) == 1
        assert data["drift"][0]["entity_id"] == "Engineering"


class TestCrossModuleConsistency:
    """Verify consistency across modules using the same data."""

    def test_exposure_scores_match_export(self, tmp_path: Path) -> None:
        roles = parse_csv(SAMPLE_CSV)
        rates = load_reference_rates(REFERENCE_PATH)
        scores = compute_org_exposure(roles, rates)

        json_path = tmp_path / "check.json"
        export_json(roles, scores, json_path, org_mean=0.5, dept_means={})
        data = json.loads(json_path.read_text())

        # Each exported score should match the computed score
        exported_map = {s["role_id"]: s for s in data["scores"]}
        for score in scores:
            exported = exported_map[score.role_id]
            assert exported["theoretical"] == score.theoretical
            assert exported["observed"] == score.observed
            assert exported["blended"] == score.blended
            assert exported["tier"] == score.tier.value

    def test_urgency_covers_all_roles(self) -> None:
        roles = parse_csv(SAMPLE_CSV)
        rates = load_reference_rates(REFERENCE_PATH)
        scores = compute_org_exposure(roles, rates)
        urgency = score_org_urgency(roles, scores, None, rates)

        role_ids = {r.role_id for r in roles}
        urgency_ids = {u.role_id for u in urgency}
        assert role_ids == urgency_ids
