"""Pydantic data models for AEDM."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from aedm.models.enums import DriftDirection, ExposureTier


class Role(BaseModel):
    """A single role in the organization's job architecture."""

    role_id: str
    title: str
    soc_code: str = ""
    department: str = "Unknown"
    headcount: int = 1
    gender_pct_female: float | None = None
    median_salary: int | None = None
    education_mode: str | None = None
    remote_pct: float | None = None

    @property
    def soc_major_group(self) -> str:
        """Extract SOC major group (e.g., '15-0000' from '15-1252')."""
        if len(self.soc_code) >= 2:
            prefix = self.soc_code[:2]
            return f"{prefix}-0000"
        return ""

    @field_validator("headcount")
    @classmethod
    def headcount_must_be_positive(cls, v: int) -> int:
        """Ensure headcount is at least 1."""
        if v < 1:
            return 1
        return v


class ExposureRate(BaseModel):
    """Reference exposure rates for a SOC major group."""

    group_name: str
    theoretical_exposure: float = Field(ge=0.0, le=1.0)
    observed_exposure: float = Field(ge=0.0, le=1.0)
    coverage_gap: float = Field(ge=0.0, le=1.0)


class ExposureScore(BaseModel):
    """Computed exposure score for a single role."""

    role_id: str
    theoretical: float = Field(ge=0.0, le=1.0)
    observed: float = Field(ge=0.0, le=1.0)
    blended: float = Field(ge=0.0, le=1.0)
    tier: ExposureTier
    soc_major_group: str


class DriftResult(BaseModel):
    """Result of drift/changepoint analysis for a role or department."""

    entity_id: str
    direction: DriftDirection
    magnitude: float
    changepoint_index: int | None = None
    p_value: float = Field(ge=0.0, le=1.0)
    trend_slope: float = 0.0
    trend_ci_lower: float = 0.0
    trend_ci_upper: float = 0.0
    n_periods: int = 0


class DemographicSegment(BaseModel):
    """Exposure analysis for a demographic segment."""

    segment_type: str  # "gender", "education", "pay_band"
    segment_value: str
    mean_exposure: float = Field(ge=0.0, le=1.0)
    disparity_ratio: float = 0.0
    headcount: int = 0
    exposure_weighted_headcount: float = 0.0
    flagged: bool = False


class UrgencyWeights(BaseModel):
    """Configurable weights for the reskilling urgency composite score."""

    exposure: float = 0.30
    drift: float = 0.25
    headcount: float = 0.25
    difficulty: float = 0.20

    @field_validator("exposure", "drift", "headcount", "difficulty")
    @classmethod
    def weight_must_be_non_negative(cls, v: float) -> float:
        """Weights must be non-negative."""
        if v < 0:
            msg = "Weights must be non-negative"
            raise ValueError(msg)
        return v


class UrgencyScore(BaseModel):
    """Composite reskilling urgency score for a role."""

    role_id: str
    score: float = Field(ge=0.0, le=1.0)
    tier: ExposureTier
    exposure_component: float = 0.0
    drift_component: float = 0.0
    headcount_component: float = 0.0
    difficulty_component: float = 0.0


class OrgSnapshot(BaseModel):
    """A point-in-time snapshot of the organization's role architecture."""

    snapshot_id: str
    period_label: str
    timestamp: datetime
    roles: list[Role] = Field(default_factory=list)
