"""Enumerations for exposure tiers, risk levels, and drift directions."""

from enum import StrEnum


class ExposureTier(StrEnum):
    """Exposure tier based on blended exposure score."""

    CRITICAL = "Critical"
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"

    @classmethod
    def from_score(cls, score: float) -> "ExposureTier":
        """Assign a tier based on a normalized [0, 1] exposure score."""
        if score >= 0.75:
            return cls.CRITICAL
        if score >= 0.50:
            return cls.HIGH
        if score >= 0.25:
            return cls.MODERATE
        return cls.LOW


class RiskLevel(StrEnum):
    """Risk level for reskilling urgency."""

    CRITICAL = "Critical"
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"


class DriftDirection(StrEnum):
    """Direction of exposure drift over time."""

    ACCELERATING = "Accelerating"
    STABLE = "Stable"
    DECELERATING = "Decelerating"
