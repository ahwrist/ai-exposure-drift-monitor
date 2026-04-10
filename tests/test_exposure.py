"""Tests for exposure index computation."""

from __future__ import annotations

from pathlib import Path

from aedm.analysis.exposure import (
    compute_exposure_index,
    compute_org_exposure,
    exposure_by_department,
    org_mean_exposure,
)
from aedm.ingest.parser import load_reference_rates, parse_csv
from aedm.models.enums import ExposureTier
from aedm.models.schemas import ExposureRate, Role


class TestComputeExposureIndex:
    """Tests for single-role exposure computation."""

    def test_high_exposure_role(
        self, sample_roles: list[Role], reference_rates: dict[str, ExposureRate]
    ) -> None:
        """Software engineer should have high blended exposure."""
        score = compute_exposure_index(sample_roles[0], reference_rates)
        assert score.theoretical == 0.94
        assert score.observed == 0.33
        assert 0.5 < score.blended < 0.7  # 0.4*0.94 + 0.6*0.33 ≈ 0.574
        assert score.tier in (ExposureTier.HIGH, ExposureTier.MODERATE)

    def test_low_exposure_role(
        self, sample_roles: list[Role], reference_rates: dict[str, ExposureRate]
    ) -> None:
        """Warehouse worker should have low blended exposure."""
        score = compute_exposure_index(sample_roles[2], reference_rates)
        assert score.blended < 0.25
        assert score.tier == ExposureTier.LOW

    def test_missing_soc_returns_zero(self, reference_rates: dict[str, ExposureRate]) -> None:
        """Role with unknown SOC group gets zero exposure."""
        role = Role(role_id="X", title="Unknown Role", soc_code="99-9999")
        score = compute_exposure_index(role, reference_rates)
        assert score.blended == 0.0
        assert score.tier == ExposureTier.LOW

    def test_custom_weights(
        self, sample_roles: list[Role], reference_rates: dict[str, ExposureRate]
    ) -> None:
        """Custom weights should change the blended score."""
        score_default = compute_exposure_index(sample_roles[0], reference_rates)
        score_theo_heavy = compute_exposure_index(
            sample_roles[0],
            reference_rates,
            weight_theoretical=0.8,
            weight_observed=0.2,
        )
        # Theoretical > observed for CS, so higher theoretical weight → higher score
        assert score_theo_heavy.blended > score_default.blended

    def test_score_normalized_to_unit_range(
        self, sample_roles: list[Role], reference_rates: dict[str, ExposureRate]
    ) -> None:
        """All scores must be in [0, 1]."""
        for role in sample_roles:
            score = compute_exposure_index(role, reference_rates)
            assert 0.0 <= score.blended <= 1.0

    def test_tier_assignment_critical(self, reference_rates: dict[str, ExposureRate]) -> None:
        """A role with very high exposure should be Critical."""
        # Create a scenario with weight_theoretical=1.0
        role = Role(role_id="X", title="Test", soc_code="15-1252")
        score = compute_exposure_index(
            role,
            reference_rates,
            weight_theoretical=1.0,
            weight_observed=0.0,
        )
        assert score.tier == ExposureTier.CRITICAL


class TestOrgExposure:
    """Tests for org-wide exposure computation."""

    def test_compute_org_exposure(
        self, sample_roles: list[Role], reference_rates: dict[str, ExposureRate]
    ) -> None:
        scores = compute_org_exposure(sample_roles, reference_rates)
        assert len(scores) == len(sample_roles)

    def test_org_mean_exposure_weighted(
        self, sample_roles: list[Role], reference_rates: dict[str, ExposureRate]
    ) -> None:
        scores = compute_org_exposure(sample_roles, reference_rates)
        mean = org_mean_exposure(sample_roles, scores)
        assert 0.0 < mean < 1.0

    def test_department_exposure(
        self, sample_roles: list[Role], reference_rates: dict[str, ExposureRate]
    ) -> None:
        scores = compute_org_exposure(sample_roles, reference_rates)
        dept_exp = exposure_by_department(sample_roles, scores)
        assert "Engineering" in dept_exp
        assert "Operations" in dept_exp
        # Engineering (CS roles) should be higher than Operations (warehouse + security)
        assert dept_exp["Engineering"] > dept_exp["Operations"]

    def test_with_sample_data(self, sample_csv_path: Path, reference_path: Path) -> None:
        roles = parse_csv(sample_csv_path)
        rates = load_reference_rates(reference_path)
        scores = compute_org_exposure(roles, rates)
        assert len(scores) == 200
        mean = org_mean_exposure(roles, scores)
        assert 0.3 < mean < 0.7  # Reasonable range for mixed org
