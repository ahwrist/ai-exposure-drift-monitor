"""Structured CSV/JSON export of computed metrics."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import structlog

from aedm.models.schemas import (
    DemographicSegment,
    DriftResult,
    ExposureScore,
    Role,
    UrgencyScore,
)

logger = structlog.get_logger()


def scores_to_dataframe(
    roles: list[Role],
    scores: list[ExposureScore],
    urgency_scores: list[UrgencyScore] | None = None,
) -> pd.DataFrame:
    """Combine roles, exposure scores, and urgency into a single DataFrame.

    Args:
        roles: List of Role objects.
        scores: Corresponding ExposureScore objects.
        urgency_scores: Optional urgency scores.

    Returns:
        DataFrame with all computed metrics per role.
    """
    role_map = {r.role_id: r for r in roles}
    urgency_map = {u.role_id: u for u in urgency_scores} if urgency_scores else {}

    rows: list[dict[str, object]] = []
    for score in scores:
        role = role_map.get(score.role_id)
        urgency = urgency_map.get(score.role_id)

        row: dict[str, object] = {
            "role_id": score.role_id,
            "title": role.title if role else "",
            "department": role.department if role else "",
            "headcount": role.headcount if role else 0,
            "soc_code": role.soc_code if role else "",
            "soc_major_group": score.soc_major_group,
            "theoretical_exposure": score.theoretical,
            "observed_exposure": score.observed,
            "blended_exposure": score.blended,
            "exposure_tier": score.tier.value,
        }

        if urgency:
            row["urgency_score"] = urgency.score
            row["urgency_tier"] = urgency.tier.value

        rows.append(row)

    return pd.DataFrame(rows)


def export_csv(
    roles: list[Role],
    scores: list[ExposureScore],
    output_path: Path,
    urgency_scores: list[UrgencyScore] | None = None,
) -> None:
    """Export exposure analysis results to CSV.

    Args:
        roles: List of Role objects.
        scores: Corresponding ExposureScore objects.
        output_path: Path for the output CSV file.
        urgency_scores: Optional urgency scores.
    """
    df = scores_to_dataframe(roles, scores, urgency_scores)
    df = df.sort_values("blended_exposure", ascending=False)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info("exported_csv", path=str(output_path), rows=len(df))


def export_json(
    roles: list[Role],
    scores: list[ExposureScore],
    output_path: Path,
    urgency_scores: list[UrgencyScore] | None = None,
    demographic_segments: list[DemographicSegment] | None = None,
    drift_results: list[DriftResult] | None = None,
    org_mean: float = 0.0,
    dept_means: dict[str, float] | None = None,
) -> None:
    """Export full analysis results to JSON.

    Args:
        roles: List of Role objects.
        scores: Corresponding ExposureScore objects.
        output_path: Path for the output JSON file.
        urgency_scores: Optional urgency scores.
        demographic_segments: Optional demographic analysis.
        drift_results: Optional drift analysis results.
        org_mean: Organization-wide mean exposure.
        dept_means: Department mean exposures.
    """
    role_map = {r.role_id: r for r in roles}
    total_headcount = sum(r.headcount for r in roles)

    result: dict[str, object] = {
        "summary": {
            "total_roles": len(roles),
            "total_headcount": total_headcount,
            "org_mean_exposure": round(org_mean, 4),
            "department_means": {dept: round(mean, 4) for dept, mean in (dept_means or {}).items()},
        },
        "scores": [
            {
                "role_id": s.role_id,
                "title": role_map.get(s.role_id, Role(role_id=s.role_id, title="")).title,
                "department": role_map.get(s.role_id, Role(role_id=s.role_id, title="")).department,
                "headcount": role_map.get(s.role_id, Role(role_id=s.role_id, title="")).headcount,
                "theoretical": s.theoretical,
                "observed": s.observed,
                "blended": s.blended,
                "tier": s.tier.value,
                "soc_major_group": s.soc_major_group,
            }
            for s in sorted(scores, key=lambda x: x.blended, reverse=True)
        ],
    }

    if urgency_scores:
        result["urgency"] = [
            {
                "role_id": u.role_id,
                "score": u.score,
                "tier": u.tier.value,
                "exposure_component": u.exposure_component,
                "drift_component": u.drift_component,
                "headcount_component": u.headcount_component,
                "difficulty_component": u.difficulty_component,
            }
            for u in urgency_scores
        ]

    if demographic_segments:
        result["demographics"] = [
            {
                "segment_type": s.segment_type,
                "segment_value": s.segment_value,
                "mean_exposure": s.mean_exposure,
                "disparity_ratio": s.disparity_ratio,
                "headcount": s.headcount,
                "flagged": s.flagged,
            }
            for s in demographic_segments
        ]

    if drift_results:
        result["drift"] = [
            {
                "entity_id": d.entity_id,
                "direction": d.direction.value,
                "magnitude": round(d.magnitude, 4),
                "changepoint_index": d.changepoint_index,
                "p_value": round(d.p_value, 4),
                "trend_slope": round(d.trend_slope, 6),
                "n_periods": d.n_periods,
            }
            for d in drift_results
        ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info("exported_json", path=str(output_path))
