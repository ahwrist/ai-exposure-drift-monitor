"""Reskilling urgency scoring."""

from __future__ import annotations

import math

import structlog

from aedm.config import settings
from aedm.models.enums import ExposureTier
from aedm.models.schemas import (
    DriftResult,
    ExposureRate,
    ExposureScore,
    Role,
    UrgencyScore,
    UrgencyWeights,
)

logger = structlog.get_logger()

DEFAULT_WEIGHTS = UrgencyWeights(
    exposure=settings.urgency_weights_exposure,
    drift=settings.urgency_weights_drift,
    headcount=settings.urgency_weights_headcount,
    difficulty=settings.urgency_weights_difficulty,
)


def estimate_reskill_difficulty(
    soc_major_group: str,
    reference_rates: dict[str, ExposureRate],
) -> float:
    """Estimate reskilling difficulty as a proxy based on exposure landscape.

    Higher difficulty means fewer nearby low-exposure occupations to transition into.

    Args:
        soc_major_group: Current role's SOC major group.
        reference_rates: Dict of SOC group to ExposureRate.

    Returns:
        Normalized difficulty score [0, 1].
    """
    if soc_major_group not in reference_rates:
        return 0.5  # Default mid-difficulty when unknown

    current_exposure = reference_rates[soc_major_group].observed_exposure

    # Find exposure rates of all other groups
    other_rates = [
        rate.observed_exposure for code, rate in reference_rates.items() if code != soc_major_group
    ]

    if not other_rates:
        return 0.5

    # Difficulty = how few groups have meaningfully lower exposure
    lower_rates = [r for r in other_rates if r < current_exposure * 0.7]

    # More lower-exposure options = easier reskilling
    fraction_accessible = len(lower_rates) / len(other_rates)

    # Invert: high accessibility = low difficulty
    difficulty = 1.0 - fraction_accessible

    return max(0.0, min(1.0, difficulty))


def _normalize_headcount(headcount: int, max_headcount: int = 100) -> float:
    """Normalize headcount using log scaling.

    Args:
        headcount: Raw headcount.
        max_headcount: Reference maximum for normalization.

    Returns:
        Normalized value [0, 1].
    """
    if headcount <= 0:
        return 0.0
    log_hc = math.log1p(headcount)
    log_max = math.log1p(max_headcount)
    return min(1.0, log_hc / log_max)


def _normalize_drift_velocity(slope: float, max_slope: float = 0.1) -> float:
    """Normalize drift slope to [0, 1].

    Args:
        slope: Raw trend slope (exposure change per period).
        max_slope: Reference maximum slope for normalization.

    Returns:
        Normalized value [0, 1].
    """
    return min(1.0, max(0.0, abs(slope) / max_slope))


def score_reskill_urgency(
    exposure: ExposureScore,
    drift: DriftResult | None,
    headcount: int,
    reskill_difficulty: float,
    weights: UrgencyWeights | None = None,
) -> UrgencyScore:
    """Compute composite reskilling urgency score.

    Args:
        exposure: Exposure score for the role.
        drift: Drift result for the role (None if single-period).
        headcount: Number of employees in the role.
        reskill_difficulty: Estimated reskilling difficulty [0, 1].
        weights: Component weights (default from config).

    Returns:
        UrgencyScore with normalized composite and tier assignment.
    """
    w = weights or DEFAULT_WEIGHTS

    # Component scores
    exposure_component = exposure.blended
    drift_component = _normalize_drift_velocity(drift.trend_slope) if drift else 0.0
    headcount_component = _normalize_headcount(headcount)
    difficulty_component = max(0.0, min(1.0, reskill_difficulty))

    # If no drift data, redistribute drift weight proportionally
    total_non_drift = w.exposure + w.headcount + w.difficulty
    scale = 1.0 / total_non_drift if total_non_drift > 0 else 0.0

    if drift is None:
        if total_non_drift > 0:
            score = (
                w.exposure * scale * exposure_component
                + w.headcount * scale * headcount_component
                + w.difficulty * scale * difficulty_component
            )
        else:
            score = 0.0
    else:
        score = (
            w.exposure * exposure_component
            + w.drift * drift_component
            + w.headcount * headcount_component
            + w.difficulty * difficulty_component
        )

    score = max(0.0, min(1.0, score))
    tier = ExposureTier.from_score(score)

    hc_comp = (
        w.headcount * headcount_component if drift else (w.headcount * scale * headcount_component)
    )
    diff_comp = (
        w.difficulty * difficulty_component
        if drift
        else (w.difficulty * scale * difficulty_component)
    )

    return UrgencyScore(
        role_id=exposure.role_id,
        score=round(score, 4),
        tier=tier,
        exposure_component=round(w.exposure * exposure_component, 4),
        drift_component=round(w.drift * drift_component if drift else 0.0, 4),
        headcount_component=round(hc_comp, 4),
        difficulty_component=round(diff_comp, 4),
    )


def score_org_urgency(
    roles: list[Role],
    scores: list[ExposureScore],
    drift_results: dict[str, DriftResult] | None,
    reference_rates: dict[str, ExposureRate],
    weights: UrgencyWeights | None = None,
) -> list[UrgencyScore]:
    """Compute urgency scores for all roles in the organization.

    Args:
        roles: List of Role objects.
        scores: Corresponding ExposureScore objects.
        drift_results: Optional dict mapping role_id to DriftResult.
        reference_rates: Reference rates for difficulty estimation.
        weights: Component weights.

    Returns:
        List of UrgencyScore objects sorted by score descending.
    """
    score_map = {s.role_id: s for s in scores}
    results: list[UrgencyScore] = []

    for role in roles:
        exposure = score_map.get(role.role_id)
        if exposure is None:
            continue

        drift = drift_results.get(role.role_id) if drift_results else None
        difficulty = estimate_reskill_difficulty(role.soc_major_group, reference_rates)

        urgency = score_reskill_urgency(
            exposure=exposure,
            drift=drift,
            headcount=role.headcount,
            reskill_difficulty=difficulty,
            weights=weights,
        )
        results.append(urgency)

    results.sort(key=lambda u: u.score, reverse=True)
    logger.info("org_urgency_complete", roles_scored=len(results))
    return results
