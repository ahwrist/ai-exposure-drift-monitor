"""Tests for demographic disparity analysis."""

from __future__ import annotations

from pathlib import Path

import pytest

from aedm.analysis.demographics import (
    analyze_all_disparities,
    analyze_education_disparity,
    analyze_gender_disparity,
    analyze_pay_band_disparity,
)
from aedm.ingest.parser import load_reference_rates, parse_csv
from aedm.analysis.exposure import compute_org_exposure
from aedm.models.schemas import ExposureScore, Role
from aedm.models.enums import ExposureTier


class TestGenderDisparity:
    """Tests for gender-based disparity analysis."""

    def test_gender_segments_created(self, sample_roles, sample_scores) -> None:
        segments = analyze_gender_disparity(sample_roles, sample_scores)
        labels = {s.segment_value for s in segments}
        assert "Female" in labels
        assert "Male" in labels

    def test_disparity_ratio_near_one_for_balanced(self) -> None:
        """When all roles have similar exposure and 50/50 gender, ratio ≈ 1."""
        roles = [
            Role(role_id="A", title="Role A", soc_code="15-1252",
                 headcount=10, gender_pct_female=0.5),
            Role(role_id="B", title="Role B", soc_code="15-1252",
                 headcount=10, gender_pct_female=0.5),
        ]
        scores = [
            ExposureScore(role_id="A", theoretical=0.5, observed=0.3,
                         blended=0.4, tier=ExposureTier.MODERATE, soc_major_group="15-0000"),
            ExposureScore(role_id="B", theoretical=0.5, observed=0.3,
                         blended=0.4, tier=ExposureTier.MODERATE, soc_major_group="15-0000"),
        ]
        segments = analyze_gender_disparity(roles, scores)
        for seg in segments:
            assert abs(seg.disparity_ratio - 1.0) < 0.01

    def test_high_female_exposure_flagged(self) -> None:
        """When female-heavy roles have higher exposure, Female should be flagged."""
        roles = [
            Role(role_id="A", title="High Exp", soc_code="15-1252",
                 headcount=10, gender_pct_female=0.9),
            Role(role_id="B", title="Low Exp", soc_code="53-7065",
                 headcount=10, gender_pct_female=0.1),
        ]
        scores = [
            ExposureScore(role_id="A", theoretical=0.9, observed=0.5,
                         blended=0.8, tier=ExposureTier.CRITICAL, soc_major_group="15-0000"),
            ExposureScore(role_id="B", theoretical=0.2, observed=0.05,
                         blended=0.1, tier=ExposureTier.LOW, soc_major_group="53-0000"),
        ]
        segments = analyze_gender_disparity(roles, scores, flag_threshold=1.2)
        female_seg = next(s for s in segments if s.segment_value == "Female")
        assert female_seg.flagged is True
        assert female_seg.disparity_ratio > 1.2

    def test_missing_gender_data_skipped(self) -> None:
        """Roles with no gender data should not cause errors."""
        roles = [Role(role_id="A", title="Test", soc_code="15-1252", headcount=5)]
        scores = [
            ExposureScore(role_id="A", theoretical=0.5, observed=0.3,
                         blended=0.4, tier=ExposureTier.MODERATE, soc_major_group="15-0000"),
        ]
        segments = analyze_gender_disparity(roles, scores)
        # No gender data → segments may be empty or zero headcount
        assert isinstance(segments, list)


class TestEducationDisparity:
    """Tests for education-based disparity analysis."""

    def test_education_segments_created(self, sample_roles, sample_scores) -> None:
        segments = analyze_education_disparity(sample_roles, sample_scores)
        labels = {s.segment_value for s in segments}
        assert "Bachelor" in labels
        assert "High School" in labels

    def test_education_headcount_sums(self, sample_roles, sample_scores) -> None:
        segments = analyze_education_disparity(sample_roles, sample_scores)
        total = sum(s.headcount for s in segments)
        expected = sum(r.headcount for r in sample_roles if r.education_mode)
        assert total == expected


class TestPayBandDisparity:
    """Tests for pay-band-based disparity analysis."""

    def test_pay_band_segments_created(self, sample_roles, sample_scores) -> None:
        segments = analyze_pay_band_disparity(sample_roles, sample_scores)
        assert len(segments) > 0
        assert all(s.segment_type == "pay_band" for s in segments)

    def test_pay_band_values_formatted(self, sample_roles, sample_scores) -> None:
        segments = analyze_pay_band_disparity(sample_roles, sample_scores)
        for seg in segments:
            assert "$" in seg.segment_value


class TestAllDisparities:
    """Tests for combined disparity analysis."""

    def test_all_segment_types_present(self, sample_roles, sample_scores) -> None:
        segments = analyze_all_disparities(sample_roles, sample_scores)
        types = {s.segment_type for s in segments}
        assert "gender" in types
        assert "education" in types
        assert "pay_band" in types

    def test_with_sample_data(self, sample_csv_path, reference_path) -> None:
        roles = parse_csv(sample_csv_path)
        rates = load_reference_rates(reference_path)
        scores = compute_org_exposure(roles, rates)
        segments = analyze_all_disparities(roles, scores)
        assert len(segments) > 0
