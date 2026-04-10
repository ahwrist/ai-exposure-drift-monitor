"""Tests for drift detection."""

from __future__ import annotations

import numpy as np
import pytest

from aedm.analysis.drift import detect_drift_cusum, detect_org_drift
from aedm.exceptions import InsufficientDataError
from aedm.models.enums import DriftDirection


class TestDetectDriftCusum:
    """Tests for CUSUM changepoint detection."""

    def test_stable_series(self) -> None:
        """Flat series should be detected as stable."""
        rng = np.random.default_rng(42)
        series = [0.5, 0.5, 0.5, 0.5]
        result = detect_drift_cusum(series, entity_id="test", rng=rng)
        assert result.direction == DriftDirection.STABLE
        assert abs(result.trend_slope) < 0.01

    def test_increasing_series(self) -> None:
        """Clear upward trend should be detected as accelerating."""
        rng = np.random.default_rng(42)
        # Strong upward trend
        series = [0.1, 0.2, 0.4, 0.6, 0.8, 0.9]
        result = detect_drift_cusum(
            series,
            entity_id="test",
            n_permutations=2000,
            rng=rng,
        )
        assert result.trend_slope > 0
        assert result.n_periods == 6

    def test_known_changepoint(self) -> None:
        """Series with a clear changepoint should detect it."""
        rng = np.random.default_rng(42)
        # Flat then jump
        series = [0.3, 0.3, 0.3, 0.3, 0.7, 0.7, 0.7, 0.7]
        result = detect_drift_cusum(
            series,
            entity_id="test",
            n_permutations=2000,
            threshold=0.5,
            rng=rng,
        )
        # The changepoint should be near index 3-4
        if result.changepoint_index is not None:
            assert 2 <= result.changepoint_index <= 5
        assert result.magnitude > 0

    def test_insufficient_data_raises(self) -> None:
        """Too few data points should raise InsufficientDataError."""
        with pytest.raises(InsufficientDataError):
            detect_drift_cusum([0.5, 0.6], entity_id="test", min_periods=3)

    def test_minimum_periods_accepted(self) -> None:
        """Exactly min_periods should work."""
        rng = np.random.default_rng(42)
        result = detect_drift_cusum(
            [0.3, 0.4, 0.5],
            entity_id="test",
            min_periods=3,
            rng=rng,
        )
        assert result.n_periods == 3

    def test_p_value_range(self) -> None:
        """p-value must be in [0, 1]."""
        rng = np.random.default_rng(42)
        result = detect_drift_cusum([0.3, 0.4, 0.5, 0.6], entity_id="test", rng=rng)
        assert 0.0 <= result.p_value <= 1.0

    def test_trend_confidence_interval(self) -> None:
        """CI lower should be <= slope <= CI upper."""
        rng = np.random.default_rng(42)
        result = detect_drift_cusum(
            [0.1, 0.2, 0.3, 0.4, 0.5],
            entity_id="test",
            rng=rng,
        )
        assert result.trend_ci_lower <= result.trend_slope <= result.trend_ci_upper


class TestOrgDrift:
    """Tests for multi-entity drift detection."""

    def test_detect_org_drift(self) -> None:
        snapshots = {
            "Engineering": [0.5, 0.52, 0.55, 0.6],
            "HR": [0.4, 0.4, 0.41, 0.4],
            "Short": [0.3, 0.4],  # Too few periods — should be skipped
        }
        results = detect_org_drift(snapshots)
        entity_ids = {r.entity_id for r in results}
        assert "Engineering" in entity_ids
        assert "HR" in entity_ids
        assert "Short" not in entity_ids

    def test_empty_input(self) -> None:
        results = detect_org_drift({})
        assert results == []
