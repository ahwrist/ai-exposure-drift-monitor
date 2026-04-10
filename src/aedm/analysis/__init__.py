"""Analysis engines for exposure, drift, demographics, and reskilling."""

from aedm.analysis.demographics import (
    analyze_all_disparities,
    analyze_education_disparity,
    analyze_gender_disparity,
    analyze_pay_band_disparity,
)
from aedm.analysis.drift import detect_drift_cusum, detect_org_drift
from aedm.analysis.exposure import (
    compute_exposure_index,
    compute_org_exposure,
    exposure_by_department,
    org_mean_exposure,
)
from aedm.analysis.reskill import (
    estimate_reskill_difficulty,
    score_org_urgency,
    score_reskill_urgency,
)

__all__ = [
    "analyze_all_disparities",
    "analyze_education_disparity",
    "analyze_gender_disparity",
    "analyze_pay_band_disparity",
    "compute_exposure_index",
    "compute_org_exposure",
    "detect_drift_cusum",
    "detect_org_drift",
    "estimate_reskill_difficulty",
    "exposure_by_department",
    "org_mean_exposure",
    "score_org_urgency",
    "score_reskill_urgency",
]
