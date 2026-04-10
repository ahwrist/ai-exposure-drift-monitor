"""Shared fixtures for AEDM tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from aedm.models.enums import ExposureTier
from aedm.models.schemas import ExposureRate, ExposureScore, Role, UrgencyWeights


SAMPLE_CSV_PATH = Path(__file__).parent.parent / "data" / "sample" / "acme_corp_roles.csv"
QUARTERLY_DIR = Path(__file__).parent.parent / "data" / "sample" / "acme_corp_quarterly"
REFERENCE_PATH = Path(__file__).parent.parent / "data" / "reference" / "anthropic_exposure_rates.json"


@pytest.fixture
def sample_roles() -> list[Role]:
    """A small set of test roles covering different exposure levels."""
    return [
        Role(
            role_id="T001",
            title="Software Engineer",
            soc_code="15-1252",
            department="Engineering",
            headcount=20,
            gender_pct_female=0.25,
            median_salary=130000,
            education_mode="Bachelor",
            remote_pct=0.9,
        ),
        Role(
            role_id="T002",
            title="Financial Analyst",
            soc_code="13-2051",
            department="Finance",
            headcount=10,
            gender_pct_female=0.55,
            median_salary=85000,
            education_mode="Bachelor",
            remote_pct=0.7,
        ),
        Role(
            role_id="T003",
            title="Warehouse Worker",
            soc_code="53-7065",
            department="Operations",
            headcount=30,
            gender_pct_female=0.15,
            median_salary=38000,
            education_mode="High School",
            remote_pct=0.0,
        ),
        Role(
            role_id="T004",
            title="HR Specialist",
            soc_code="13-1071",
            department="HR",
            headcount=5,
            gender_pct_female=0.78,
            median_salary=65000,
            education_mode="Bachelor",
            remote_pct=0.6,
        ),
        Role(
            role_id="T005",
            title="Security Guard",
            soc_code="33-9032",
            department="Operations",
            headcount=8,
            gender_pct_female=0.12,
            median_salary=35000,
            education_mode="High School",
            remote_pct=0.0,
        ),
    ]


@pytest.fixture
def reference_rates() -> dict[str, ExposureRate]:
    """Reference rates for test SOC groups."""
    return {
        "15-0000": ExposureRate(
            group_name="Computer and Mathematical",
            theoretical_exposure=0.94,
            observed_exposure=0.33,
            coverage_gap=0.61,
        ),
        "13-0000": ExposureRate(
            group_name="Business and Financial Operations",
            theoretical_exposure=0.943,
            observed_exposure=0.20,
            coverage_gap=0.743,
        ),
        "53-0000": ExposureRate(
            group_name="Transportation and Material Moving",
            theoretical_exposure=0.38,
            observed_exposure=0.03,
            coverage_gap=0.35,
        ),
        "33-0000": ExposureRate(
            group_name="Protective Service",
            theoretical_exposure=0.52,
            observed_exposure=0.05,
            coverage_gap=0.47,
        ),
        "11-0000": ExposureRate(
            group_name="Management",
            theoretical_exposure=0.913,
            observed_exposure=0.18,
            coverage_gap=0.733,
        ),
        "37-0000": ExposureRate(
            group_name="Building and Grounds Cleaning and Maintenance",
            theoretical_exposure=0.28,
            observed_exposure=0.02,
            coverage_gap=0.26,
        ),
    }


@pytest.fixture
def sample_scores() -> list[ExposureScore]:
    """Pre-computed exposure scores matching sample_roles fixture."""
    return [
        ExposureScore(
            role_id="T001", theoretical=0.94, observed=0.33,
            blended=0.574, tier=ExposureTier.HIGH, soc_major_group="15-0000",
        ),
        ExposureScore(
            role_id="T002", theoretical=0.943, observed=0.20,
            blended=0.4972, tier=ExposureTier.MODERATE, soc_major_group="13-0000",
        ),
        ExposureScore(
            role_id="T003", theoretical=0.38, observed=0.03,
            blended=0.17, tier=ExposureTier.LOW, soc_major_group="53-0000",
        ),
        ExposureScore(
            role_id="T004", theoretical=0.943, observed=0.20,
            blended=0.4972, tier=ExposureTier.MODERATE, soc_major_group="13-0000",
        ),
        ExposureScore(
            role_id="T005", theoretical=0.52, observed=0.05,
            blended=0.238, tier=ExposureTier.LOW, soc_major_group="33-0000",
        ),
    ]


@pytest.fixture
def sample_csv_path() -> Path:
    """Path to the full sample CSV data."""
    return SAMPLE_CSV_PATH


@pytest.fixture
def quarterly_dir() -> Path:
    """Path to the quarterly snapshot directory."""
    return QUARTERLY_DIR


@pytest.fixture
def reference_path() -> Path:
    """Path to the reference rates JSON."""
    return REFERENCE_PATH
