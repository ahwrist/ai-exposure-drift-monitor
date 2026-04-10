"""Tests for reskilling urgency scoring."""

from __future__ import annotations

from pathlib import Path

from aedm.analysis.exposure import compute_org_exposure
from aedm.analysis.reskill import (
    estimate_reskill_difficulty,
    score_org_urgency,
    score_reskill_urgency,
)
from aedm.ingest.parser import load_reference_rates, parse_csv
from aedm.models.enums import DriftDirection, ExposureTier
from aedm.models.schemas import (
    DriftResult,
    ExposureRate,
    ExposureScore,
    Role,
    UrgencyWeights,
)


class TestEstimateReskillDifficulty:
    """Tests for reskill difficulty estimation."""

    def test_low_exposure_group_higher_difficulty(
        self, reference_rates: dict[str, ExposureRate]
    ) -> None:
        """Low-exposure SOC groups have higher difficulty (fewer *lower* safe harbors)."""
        cs_difficulty = estimate_reskill_difficulty("15-0000", reference_rates)
        ops_difficulty = estimate_reskill_difficulty("53-0000", reference_rates)
        # CS has highest observed exposure → most other groups are lower → low difficulty
        # Ops has low observed exposure → few groups even lower → high difficulty
        assert ops_difficulty > cs_difficulty

    def test_unknown_soc_returns_default(self, reference_rates: dict[str, ExposureRate]) -> None:
        difficulty = estimate_reskill_difficulty("99-0000", reference_rates)
        assert difficulty == 0.5

    def test_difficulty_in_unit_range(self, reference_rates: dict[str, ExposureRate]) -> None:
        for soc in reference_rates:
            d = estimate_reskill_difficulty(soc, reference_rates)
            assert 0.0 <= d <= 1.0


class TestScoreReskillUrgency:
    """Tests for composite urgency scoring."""

    def test_high_exposure_high_urgency(self) -> None:
        """A role with high exposure, drift, headcount, and difficulty should score high."""
        exposure = ExposureScore(
            role_id="X",
            theoretical=0.94,
            observed=0.33,
            blended=0.8,
            tier=ExposureTier.CRITICAL,
            soc_major_group="15-0000",
        )
        drift = DriftResult(
            entity_id="X",
            direction=DriftDirection.ACCELERATING,
            magnitude=2.0,
            p_value=0.01,
            trend_slope=0.08,
            n_periods=6,
        )
        result = score_reskill_urgency(exposure, drift, headcount=50, reskill_difficulty=0.8)
        assert result.score > 0.5
        assert result.tier in (ExposureTier.CRITICAL, ExposureTier.HIGH)

    def test_low_exposure_low_urgency(self) -> None:
        """A role with low exposure and no drift should score low."""
        exposure = ExposureScore(
            role_id="X",
            theoretical=0.1,
            observed=0.02,
            blended=0.05,
            tier=ExposureTier.LOW,
            soc_major_group="53-0000",
        )
        result = score_reskill_urgency(exposure, None, headcount=3, reskill_difficulty=0.1)
        assert result.score < 0.25
        assert result.tier == ExposureTier.LOW

    def test_no_drift_data_still_scores(self) -> None:
        """Urgency should work without drift data (single-period analysis)."""
        exposure = ExposureScore(
            role_id="X",
            theoretical=0.5,
            observed=0.2,
            blended=0.4,
            tier=ExposureTier.MODERATE,
            soc_major_group="15-0000",
        )
        result = score_reskill_urgency(exposure, None, headcount=10, reskill_difficulty=0.5)
        assert result.drift_component == 0.0
        assert result.score > 0.0

    def test_custom_weights(self) -> None:
        """Custom weights should change the score."""
        exposure = ExposureScore(
            role_id="X",
            theoretical=0.5,
            observed=0.3,
            blended=0.4,
            tier=ExposureTier.MODERATE,
            soc_major_group="15-0000",
        )
        default_result = score_reskill_urgency(exposure, None, headcount=10, reskill_difficulty=0.5)
        heavy_exposure = score_reskill_urgency(
            exposure,
            None,
            headcount=10,
            reskill_difficulty=0.5,
            weights=UrgencyWeights(exposure=0.8, drift=0.0, headcount=0.1, difficulty=0.1),
        )
        # With 80% weight on exposure=0.4, score should be dominated by that
        assert heavy_exposure.score != default_result.score

    def test_score_in_unit_range(self) -> None:
        exposure = ExposureScore(
            role_id="X",
            theoretical=0.99,
            observed=0.99,
            blended=0.99,
            tier=ExposureTier.CRITICAL,
            soc_major_group="15-0000",
        )
        drift = DriftResult(
            entity_id="X",
            direction=DriftDirection.ACCELERATING,
            magnitude=5.0,
            p_value=0.001,
            trend_slope=0.2,
            n_periods=8,
        )
        result = score_reskill_urgency(exposure, drift, headcount=100, reskill_difficulty=1.0)
        assert 0.0 <= result.score <= 1.0

    def test_tier_assignment(self) -> None:
        """Verify tier assignments match score ranges."""
        for blended, expected_tier in [
            (0.9, ExposureTier.CRITICAL),
            (0.6, ExposureTier.HIGH),
            (0.35, ExposureTier.MODERATE),
            (0.1, ExposureTier.LOW),
        ]:
            exposure = ExposureScore(
                role_id="X",
                theoretical=blended,
                observed=blended,
                blended=blended,
                tier=ExposureTier.from_score(blended),
                soc_major_group="15-0000",
            )
            # Use weights that make score ≈ blended
            result = score_reskill_urgency(
                exposure,
                None,
                headcount=1,
                reskill_difficulty=blended,
                weights=UrgencyWeights(exposure=1.0, drift=0.0, headcount=0.0, difficulty=0.0),
            )
            assert result.tier == expected_tier


class TestOrgUrgency:
    """Tests for org-wide urgency scoring."""

    def test_org_urgency_sorted_descending(
        self,
        sample_roles: list[Role],
        sample_scores: list[ExposureScore],
        reference_rates: dict[str, ExposureRate],
    ) -> None:
        results = score_org_urgency(sample_roles, sample_scores, None, reference_rates)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_org_urgency_covers_all_roles(
        self,
        sample_roles: list[Role],
        sample_scores: list[ExposureScore],
        reference_rates: dict[str, ExposureRate],
    ) -> None:
        results = score_org_urgency(sample_roles, sample_scores, None, reference_rates)
        assert len(results) == len(sample_roles)

    def test_with_sample_data(self, sample_csv_path: Path, reference_path: Path) -> None:
        roles = parse_csv(sample_csv_path)
        rates = load_reference_rates(reference_path)
        scores = compute_org_exposure(roles, rates)
        results = score_org_urgency(roles, scores, None, rates)
        assert len(results) == 200
        assert all(0.0 <= r.score <= 1.0 for r in results)
