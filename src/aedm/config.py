"""Configuration and settings for AEDM."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class AEDMSettings(BaseSettings):
    """Application settings with defaults and environment overrides."""

    # Paths
    data_dir: Path = Path("data")
    reference_rates_path: Path = Path("data/reference/anthropic_exposure_rates.json")
    output_dir: Path = Path("report")

    # Exposure computation
    weight_theoretical: float = Field(default=0.4, ge=0.0, le=1.0)
    weight_observed: float = Field(default=0.6, ge=0.0, le=1.0)

    # Drift detection
    cusum_threshold: float = Field(default=1.5, gt=0.0)
    drift_min_periods: int = Field(default=3, ge=2)
    drift_permutations: int = Field(default=1000, ge=100)
    drift_significance_level: float = Field(default=0.05, gt=0.0, lt=1.0)

    # Demographics
    disparity_flag_threshold: float = Field(default=1.2, gt=1.0)
    pay_band_boundaries: list[int] = Field(default=[50000, 80000, 120000, 160000, 200000])

    # Urgency scoring
    urgency_weights_exposure: float = 0.30
    urgency_weights_drift: float = 0.25
    urgency_weights_headcount: float = 0.25
    urgency_weights_difficulty: float = 0.20

    # Visualization color palette
    color_navy: str = "#1B2A4A"
    color_teal: str = "#2EC4B6"
    color_amber: str = "#FF6B35"
    color_gray: str = "#E8E8E8"
    color_red: str = "#E63946"

    # Fuzzy matching
    fuzzy_match_threshold: int = Field(default=80, ge=0, le=100)

    model_config = {"env_prefix": "AEDM_"}


# Singleton settings instance
settings = AEDMSettings()
