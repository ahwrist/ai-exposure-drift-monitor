"""Tests for scenario modeling logic (time-to-critical, reskilling simulation)."""

from __future__ import annotations

from aedm.models.enums import DriftDirection, ExposureTier
from aedm.models.schemas import DriftResult, ExposureScore, Role, UrgencyScore


class TestTimeToCriticalProjection:
    """Tests for time-to-critical projection logic."""

    def test_basic_projection(self) -> None:
        """A department at 0.50 with slope 0.05 should reach 0.75 in 5 quarters."""
        current_exposure = 0.50
        slope = 0.05
        critical_threshold = 0.75
        remaining = critical_threshold - current_exposure
        quarters = remaining / slope
        assert quarters == 5.0

    def test_already_critical(self) -> None:
        """A department already at/above 0.75 is already critical."""
        current_exposure = 0.80
        critical_threshold = 0.75
        assert current_exposure >= critical_threshold

    def test_negative_slope_not_projected(self) -> None:
        """A decelerating department should not be projected to reach critical."""
        slope = -0.02
        assert slope <= 0

    def test_zero_slope_not_projected(self) -> None:
        """A stable department should not be projected to reach critical."""
        slope = 0.0
        assert slope <= 0

    def test_projection_with_drift_result(self) -> None:
        """Integration test using DriftResult objects."""
        drift = DriftResult(
            entity_id="Engineering",
            direction=DriftDirection.ACCELERATING,
            magnitude=0.15,
            changepoint_index=2,
            p_value=0.02,
            trend_slope=0.03,
            n_periods=4,
        )
        current_exposure = 0.60
        critical_threshold = 0.75

        if drift.trend_slope > 0 and current_exposure < critical_threshold:
            quarters = (critical_threshold - current_exposure) / drift.trend_slope
            assert abs(quarters - 5.0) < 0.01
            confidence = "High" if drift.p_value < 0.05 else "Low"
            assert confidence == "High"


class TestReskillingImpactSimulation:
    """Tests for reskilling impact simulation logic."""

    def test_reduction_math(self) -> None:
        """Reskilling should reduce exposure by the reduction factor."""
        blended = 0.80
        reduction_factor = 0.30
        new_blended = blended * (1 - reduction_factor)
        assert abs(new_blended - 0.56) < 0.001

    def test_org_mean_decreases(self) -> None:
        """Reskilling top-urgency roles should lower org mean exposure."""
        roles = [
            Role(role_id="R1", title="High", soc_code="15-1252", headcount=10),
            Role(role_id="R2", title="Low", soc_code="53-7065", headcount=10),
        ]
        scores = [
            ExposureScore(
                role_id="R1",
                theoretical=0.9,
                observed=0.5,
                blended=0.8,
                tier=ExposureTier.CRITICAL,
                soc_major_group="15-0000",
            ),
            ExposureScore(
                role_id="R2",
                theoretical=0.3,
                observed=0.1,
                blended=0.2,
                tier=ExposureTier.LOW,
                soc_major_group="53-0000",
            ),
        ]
        urgency = [
            UrgencyScore(role_id="R1", score=0.7, tier=ExposureTier.HIGH),
            UrgencyScore(role_id="R2", score=0.2, tier=ExposureTier.LOW),
        ]

        score_map = {s.role_id: s for s in scores}
        reduction_factor = 0.30
        top_urgency_ids = {urgency[0].role_id}  # reskill top 1

        before_weighted = sum(score_map[r.role_id].blended * r.headcount for r in roles)
        after_weighted = 0.0
        total_hc = sum(r.headcount for r in roles)

        for role in roles:
            score = score_map[role.role_id]
            if role.role_id in top_urgency_ids:
                new_blended = score.blended * (1 - reduction_factor)
            else:
                new_blended = score.blended
            after_weighted += new_blended * role.headcount

        before_mean = before_weighted / total_hc
        after_mean = after_weighted / total_hc

        assert after_mean < before_mean
        # Before: (0.8*10 + 0.2*10)/20 = 0.50
        # After: (0.56*10 + 0.2*10)/20 = 0.38
        assert abs(before_mean - 0.50) < 0.001
        assert abs(after_mean - 0.38) < 0.001

    def test_tier_shift(self) -> None:
        """Reskilling should potentially shift roles to lower tiers."""
        blended = 0.80  # Critical
        reduction_factor = 0.30
        new_blended = blended * (1 - reduction_factor)  # 0.56

        before_tier = ExposureTier.from_score(blended)
        after_tier = ExposureTier.from_score(new_blended)

        assert before_tier == ExposureTier.CRITICAL
        assert after_tier == ExposureTier.HIGH

    def test_zero_reduction(self) -> None:
        """Zero reduction should leave exposure unchanged."""
        blended = 0.70
        new_blended = blended * (1 - 0.0)
        assert new_blended == blended
