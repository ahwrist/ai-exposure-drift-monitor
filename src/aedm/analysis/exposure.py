"""Core exposure index computation engine."""

from __future__ import annotations

import structlog

from aedm.config import settings
from aedm.models.enums import ExposureTier
from aedm.models.schemas import ExposureRate, ExposureScore, Role

logger = structlog.get_logger()


def compute_exposure_index(
    role: Role,
    reference_rates: dict[str, ExposureRate],
    weight_theoretical: float | None = None,
    weight_observed: float | None = None,
) -> ExposureScore:
    """Compute blended exposure index for a single role.

    Weights observed exposure more heavily because it reflects
    actual adoption patterns, not just theoretical feasibility.

    Args:
        role: The role to score.
        reference_rates: Dict mapping SOC major group to ExposureRate.
        weight_theoretical: Override for theoretical weight (default from config).
        weight_observed: Override for observed weight (default from config).

    Returns:
        ExposureScore with theoretical, observed, blended, and tier.
    """
    wt = weight_theoretical if weight_theoretical is not None else settings.weight_theoretical
    wo = weight_observed if weight_observed is not None else settings.weight_observed

    major_group = role.soc_major_group

    if major_group and major_group in reference_rates:
        rate = reference_rates[major_group]
        theoretical = rate.theoretical_exposure
        observed = rate.observed_exposure
    else:
        logger.warning(
            "no_reference_rate",
            role_id=role.role_id,
            soc_major_group=major_group,
        )
        theoretical = 0.0
        observed = 0.0

    # Normalize weights to sum to 1
    total_weight = wt + wo
    if total_weight > 0:
        wt_norm = wt / total_weight
        wo_norm = wo / total_weight
    else:
        wt_norm = 0.5
        wo_norm = 0.5

    blended = wt_norm * theoretical + wo_norm * observed
    blended = max(0.0, min(1.0, blended))

    tier = ExposureTier.from_score(blended)

    return ExposureScore(
        role_id=role.role_id,
        theoretical=theoretical,
        observed=observed,
        blended=blended,
        tier=tier,
        soc_major_group=major_group,
    )


def compute_org_exposure(
    roles: list[Role],
    reference_rates: dict[str, ExposureRate],
    weight_theoretical: float | None = None,
    weight_observed: float | None = None,
) -> list[ExposureScore]:
    """Compute exposure indices for all roles in an organization.

    Args:
        roles: List of Role objects.
        reference_rates: Dict mapping SOC major group to ExposureRate.
        weight_theoretical: Override for theoretical weight.
        weight_observed: Override for observed weight.

    Returns:
        List of ExposureScore objects, one per role.
    """
    scores = [
        compute_exposure_index(role, reference_rates, weight_theoretical, weight_observed)
        for role in roles
    ]
    logger.info("computed_org_exposure", role_count=len(scores))
    return scores


def org_mean_exposure(
    roles: list[Role],
    scores: list[ExposureScore],
) -> float:
    """Compute headcount-weighted mean exposure across the organization.

    Args:
        roles: List of Role objects (for headcount).
        scores: Corresponding ExposureScore objects.

    Returns:
        Weighted mean blended exposure score.
    """
    role_map = {r.role_id: r for r in roles}
    total_headcount = 0
    weighted_sum = 0.0

    for score in scores:
        role = role_map.get(score.role_id)
        hc = role.headcount if role else 1
        weighted_sum += score.blended * hc
        total_headcount += hc

    if total_headcount == 0:
        return 0.0
    return weighted_sum / total_headcount


def exposure_by_department(
    roles: list[Role],
    scores: list[ExposureScore],
) -> dict[str, float]:
    """Compute headcount-weighted mean exposure by department.

    Args:
        roles: List of Role objects.
        scores: Corresponding ExposureScore objects.

    Returns:
        Dict mapping department name to mean blended exposure.
    """
    score_map = {s.role_id: s for s in scores}
    dept_hc: dict[str, int] = {}
    dept_weighted: dict[str, float] = {}

    for role in roles:
        score = score_map.get(role.role_id)
        if score is None:
            continue
        dept = role.department
        dept_hc[dept] = dept_hc.get(dept, 0) + role.headcount
        dept_weighted[dept] = dept_weighted.get(dept, 0.0) + score.blended * role.headcount

    return {
        dept: dept_weighted[dept] / dept_hc[dept]
        for dept in dept_hc
        if dept_hc[dept] > 0
    }
