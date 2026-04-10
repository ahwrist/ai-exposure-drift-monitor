"""Drift detection via CUSUM changepoint analysis and linear trend estimation."""

from __future__ import annotations

import numpy as np
import structlog
from scipy import stats

from aedm.config import settings
from aedm.exceptions import InsufficientDataError
from aedm.models.enums import DriftDirection
from aedm.models.schemas import DriftResult

logger = structlog.get_logger()


def _cusum_statistic(series: np.ndarray) -> tuple[float, int]:
    """Compute the CUSUM statistic and estimated changepoint index.

    Args:
        series: 1-D array of exposure scores over time.

    Returns:
        Tuple of (cusum_statistic, changepoint_index).
    """
    mean = np.mean(series)
    cumsum = np.cumsum(series - mean)
    max_val = np.max(cumsum)
    min_val = np.min(cumsum)
    cusum_stat = float(max_val - min_val)
    changepoint = int(np.argmax(np.abs(cumsum)))
    return cusum_stat, changepoint


def _permutation_p_value(
    series: np.ndarray,
    observed_stat: float,
    n_permutations: int,
    rng: np.random.Generator | None = None,
) -> float:
    """Assess significance via permutation testing.

    Args:
        series: Original time series.
        observed_stat: CUSUM statistic from the observed series.
        n_permutations: Number of random permutations.
        rng: Optional random number generator for reproducibility.

    Returns:
        p-value: proportion of permuted statistics >= observed.
    """
    if rng is None:
        rng = np.random.default_rng()

    count_exceeding = 0
    for _ in range(n_permutations):
        permuted = rng.permutation(series)
        perm_stat, _ = _cusum_statistic(permuted)
        if perm_stat >= observed_stat:
            count_exceeding += 1

    return count_exceeding / n_permutations


def _linear_trend(series: np.ndarray) -> tuple[float, float, float]:
    """Fit a simple linear trend via OLS.

    Args:
        series: 1-D array of exposure scores.

    Returns:
        Tuple of (slope, ci_lower, ci_upper) for 95% confidence interval.
    """
    n = len(series)
    x = np.arange(n, dtype=float)
    result = stats.linregress(x, series)
    slope = float(result.slope)

    # 95% CI for slope
    t_crit = float(stats.t.ppf(0.975, df=n - 2))
    ci_half = t_crit * float(result.stderr)

    return slope, slope - ci_half, slope + ci_half


def detect_drift_cusum(
    exposure_series: list[float],
    entity_id: str = "",
    threshold: float | None = None,
    min_periods: int | None = None,
    n_permutations: int | None = None,
    significance_level: float | None = None,
    rng: np.random.Generator | None = None,
) -> DriftResult:
    """CUSUM changepoint detection on exposure time series.

    Args:
        exposure_series: List of exposure scores over time.
        entity_id: Identifier for the role or department.
        threshold: CUSUM threshold for detection (default from config).
        min_periods: Minimum required time periods (default from config).
        n_permutations: Number of permutations for p-value (default from config).
        significance_level: P-value threshold (default from config).
        rng: Random number generator for reproducibility.

    Returns:
        DriftResult with direction, magnitude, changepoint, and significance.

    Raises:
        InsufficientDataError: If fewer than min_periods data points provided.
    """
    _threshold = threshold if threshold is not None else settings.cusum_threshold
    _min = min_periods if min_periods is not None else settings.drift_min_periods
    _n_perm = n_permutations if n_permutations is not None else settings.drift_permutations
    _sig = (
        significance_level if significance_level is not None else settings.drift_significance_level
    )

    n = len(exposure_series)
    if n < _min:
        raise InsufficientDataError("Drift detection", _min, n)

    series = np.array(exposure_series, dtype=float)

    # CUSUM
    cusum_stat, changepoint_idx = _cusum_statistic(series)

    # Permutation test
    p_value = _permutation_p_value(series, cusum_stat, _n_perm, rng=rng)

    # Linear trend
    slope, ci_lower, ci_upper = _linear_trend(series)

    # Determine direction
    if p_value < _sig and cusum_stat > _threshold:
        direction = DriftDirection.ACCELERATING if slope > 0 else DriftDirection.DECELERATING
        cp_index: int | None = changepoint_idx
    else:
        direction = DriftDirection.STABLE
        cp_index = None

    result = DriftResult(
        entity_id=entity_id,
        direction=direction,
        magnitude=cusum_stat,
        changepoint_index=cp_index,
        p_value=p_value,
        trend_slope=slope,
        trend_ci_lower=ci_lower,
        trend_ci_upper=ci_upper,
        n_periods=n,
    )

    logger.info(
        "drift_detected",
        entity_id=entity_id,
        direction=direction.value,
        p_value=round(p_value, 4),
        slope=round(slope, 6),
    )

    return result


def detect_org_drift(
    snapshots_by_entity: dict[str, list[float]],
    **kwargs: object,
) -> list[DriftResult]:
    """Run drift detection for multiple entities.

    Args:
        snapshots_by_entity: Dict mapping entity_id to list of exposure scores over time.
        **kwargs: Additional arguments passed to detect_drift_cusum.

    Returns:
        List of DriftResult objects.
    """
    results: list[DriftResult] = []
    _raw_min = kwargs.get("min_periods")
    min_periods = int(str(_raw_min)) if _raw_min is not None else settings.drift_min_periods

    for entity_id, series in snapshots_by_entity.items():
        if len(series) < min_periods:
            logger.debug(
                "skipping_drift_insufficient_data",
                entity_id=entity_id,
                periods=len(series),
            )
            continue
        result = detect_drift_cusum(series, entity_id=entity_id, **kwargs)  # type: ignore[arg-type]
        results.append(result)

    logger.info("org_drift_complete", entities_analyzed=len(results))
    return results
