"""Demographic disparity analysis for AI exposure."""

from __future__ import annotations

import structlog

from aedm.config import settings
from aedm.models.schemas import DemographicSegment, ExposureScore, Role

logger = structlog.get_logger()


def _assign_pay_band(salary: int) -> str:
    """Assign a salary to a pay band label.

    Args:
        salary: Annual salary in USD.

    Returns:
        Pay band label string.
    """
    boundaries = settings.pay_band_boundaries
    for i, upper in enumerate(boundaries):
        if salary < upper:
            lower = boundaries[i - 1] if i > 0 else 0
            return f"${lower // 1000}K-${upper // 1000}K"
    return f"${boundaries[-1] // 1000}K+"


def analyze_gender_disparity(
    roles: list[Role],
    scores: list[ExposureScore],
    flag_threshold: float | None = None,
) -> list[DemographicSegment]:
    """Analyze exposure disparity by gender.

    Segments workforce into Female-majority and Male-majority based on
    gender_pct_female. Computes exposure-weighted headcount and disparity ratios.

    Args:
        roles: List of Role objects with gender_pct_female.
        scores: Corresponding ExposureScore objects.
        flag_threshold: Disparity ratio threshold for flagging (default from config).

    Returns:
        List of DemographicSegment objects for gender analysis.
    """
    threshold = flag_threshold if flag_threshold is not None else settings.disparity_flag_threshold
    score_map = {s.role_id: s for s in scores}

    # Compute org-wide mean exposure
    total_hc = 0
    total_weighted = 0.0
    for role in roles:
        score = score_map.get(role.role_id)
        if score:
            total_hc += role.headcount
            total_weighted += score.blended * role.headcount
    org_mean = total_weighted / total_hc if total_hc > 0 else 0.0

    # Segment by gender (using headcount proportions)
    segments: dict[str, dict[str, float]] = {
        "Female": {"headcount": 0.0, "weighted_exposure": 0.0},
        "Male": {"headcount": 0.0, "weighted_exposure": 0.0},
    }

    for role in roles:
        score = score_map.get(role.role_id)
        if score is None or role.gender_pct_female is None:
            continue

        female_hc = role.headcount * role.gender_pct_female
        male_hc = role.headcount * (1 - role.gender_pct_female)

        segments["Female"]["headcount"] += female_hc
        segments["Female"]["weighted_exposure"] += score.blended * female_hc
        segments["Male"]["headcount"] += male_hc
        segments["Male"]["weighted_exposure"] += score.blended * male_hc

    results: list[DemographicSegment] = []
    for label, data in segments.items():
        hc = data["headcount"]
        if hc > 0:
            mean_exp = data["weighted_exposure"] / hc
            ratio = mean_exp / org_mean if org_mean > 0 else 0.0
            results.append(DemographicSegment(
                segment_type="gender",
                segment_value=label,
                mean_exposure=round(mean_exp, 4),
                disparity_ratio=round(ratio, 4),
                headcount=int(round(hc)),
                exposure_weighted_headcount=round(data["weighted_exposure"], 2),
                flagged=ratio > threshold,
            ))

    return results


def analyze_education_disparity(
    roles: list[Role],
    scores: list[ExposureScore],
    flag_threshold: float | None = None,
) -> list[DemographicSegment]:
    """Analyze exposure disparity by education level.

    Args:
        roles: List of Role objects with education_mode.
        scores: Corresponding ExposureScore objects.
        flag_threshold: Disparity ratio threshold for flagging.

    Returns:
        List of DemographicSegment objects for education analysis.
    """
    threshold = flag_threshold if flag_threshold is not None else settings.disparity_flag_threshold
    score_map = {s.role_id: s for s in scores}

    total_hc = 0
    total_weighted = 0.0
    edu_data: dict[str, dict[str, float]] = {}

    for role in roles:
        score = score_map.get(role.role_id)
        if score is None:
            continue
        total_hc += role.headcount
        total_weighted += score.blended * role.headcount

        if role.education_mode:
            edu = role.education_mode
            if edu not in edu_data:
                edu_data[edu] = {"headcount": 0.0, "weighted_exposure": 0.0}
            edu_data[edu]["headcount"] += role.headcount
            edu_data[edu]["weighted_exposure"] += score.blended * role.headcount

    org_mean = total_weighted / total_hc if total_hc > 0 else 0.0

    results: list[DemographicSegment] = []
    for edu_level, data in sorted(edu_data.items()):
        hc = data["headcount"]
        if hc > 0:
            mean_exp = data["weighted_exposure"] / hc
            ratio = mean_exp / org_mean if org_mean > 0 else 0.0
            results.append(DemographicSegment(
                segment_type="education",
                segment_value=edu_level,
                mean_exposure=round(mean_exp, 4),
                disparity_ratio=round(ratio, 4),
                headcount=int(round(hc)),
                exposure_weighted_headcount=round(data["weighted_exposure"], 2),
                flagged=ratio > threshold,
            ))

    return results


def analyze_pay_band_disparity(
    roles: list[Role],
    scores: list[ExposureScore],
    flag_threshold: float | None = None,
) -> list[DemographicSegment]:
    """Analyze exposure disparity by pay band.

    Args:
        roles: List of Role objects with median_salary.
        scores: Corresponding ExposureScore objects.
        flag_threshold: Disparity ratio threshold for flagging.

    Returns:
        List of DemographicSegment objects for pay band analysis.
    """
    threshold = flag_threshold if flag_threshold is not None else settings.disparity_flag_threshold
    score_map = {s.role_id: s for s in scores}

    total_hc = 0
    total_weighted = 0.0
    band_data: dict[str, dict[str, float]] = {}

    for role in roles:
        score = score_map.get(role.role_id)
        if score is None:
            continue
        total_hc += role.headcount
        total_weighted += score.blended * role.headcount

        if role.median_salary is not None:
            band = _assign_pay_band(role.median_salary)
            if band not in band_data:
                band_data[band] = {"headcount": 0.0, "weighted_exposure": 0.0}
            band_data[band]["headcount"] += role.headcount
            band_data[band]["weighted_exposure"] += score.blended * role.headcount

    org_mean = total_weighted / total_hc if total_hc > 0 else 0.0

    results: list[DemographicSegment] = []
    for band, data in sorted(band_data.items()):
        hc = data["headcount"]
        if hc > 0:
            mean_exp = data["weighted_exposure"] / hc
            ratio = mean_exp / org_mean if org_mean > 0 else 0.0
            results.append(DemographicSegment(
                segment_type="pay_band",
                segment_value=band,
                mean_exposure=round(mean_exp, 4),
                disparity_ratio=round(ratio, 4),
                headcount=int(round(hc)),
                exposure_weighted_headcount=round(data["weighted_exposure"], 2),
                flagged=ratio > threshold,
            ))

    return results


def analyze_all_disparities(
    roles: list[Role],
    scores: list[ExposureScore],
    flag_threshold: float | None = None,
) -> list[DemographicSegment]:
    """Run all demographic disparity analyses.

    Args:
        roles: List of Role objects.
        scores: Corresponding ExposureScore objects.
        flag_threshold: Disparity ratio threshold for flagging.

    Returns:
        Combined list of DemographicSegment objects across all dimensions.
    """
    results: list[DemographicSegment] = []
    results.extend(analyze_gender_disparity(roles, scores, flag_threshold))
    results.extend(analyze_education_disparity(roles, scores, flag_threshold))
    results.extend(analyze_pay_band_disparity(roles, scores, flag_threshold))

    flagged = [s for s in results if s.flagged]
    logger.info(
        "disparity_analysis_complete",
        total_segments=len(results),
        flagged_segments=len(flagged),
    )

    return results
