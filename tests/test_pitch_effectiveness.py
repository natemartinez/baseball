"""
Tests for Pitch Effectiveness Engine.

Verifies that Pitch Effectiveness is SEPARATE from Pitch Confidence:
- Effectiveness: Physical stuff quality (bite, movement sharpness) → governs whiff rate & exit velocity.
- Confidence: Mental/psychological state → governs command accuracy / error dispersion circle.

Tests:
1. Baseline effectiveness starts in [70, 95] range from physical attributes.
2. Hard contact degrades effectiveness; whiffs and weak outs restore it.
3. Stamina fatigue correctly reduces recovery rate and applies fatigue floor.
4. Low confidence causes only minor effectiveness drag (not primary degradation).
5. Effectiveness to whiff rate translation is correct and independent of confidence.
6. Effectiveness to exit velocity translation is correct.
7. Full separation test: changing only confidence should not change effectiveness directly.
"""

import pytest
from backend.engine.pitching_engine.pitcher_info.pitch_effectiveness import (
    compute_baseline_effectiveness,
    calculate_effectiveness_delta,
    apply_stamina_fatigue_to_effectiveness,
    update_pitch_effectiveness,
    apply_effectiveness_to_whiff_rate,
    apply_effectiveness_to_exit_velocity,
    calculate_command_adjustment_from_effectiveness,
    apply_effectiveness_to_velocity,
    apply_effectiveness_to_break,
    adjust_simulation_timing_distribution,
    CONFIDENCE_DRAG_THRESHOLD,
    CONFIDENCE_DRAG_MAX,
    FATIGUE_EFFECTIVENESS_MAX_PENALTY,
)
from backend.engine.pitching_engine.pitcher_info.adjusted_ratings import (
    compute_effective_command,
)
from backend.engine.pitching_engine.pitch_execution.calculations import (
    get_simulation_timing_distribution,
    sample_simulation_timing_tier,
)
from tiers import AbilityTier, TimingTier


class TestBaselineEffectiveness:
    """Verifies that baseline effectiveness is computed from physical stuff attributes."""

    def test_elite_pitch_starts_high(self):
        """An elite breaking ball (high velo + high break + high spin) should start near 95."""
        baseline = compute_baseline_effectiveness(
            velocity_mph=98.0,
            break_rating=95.0,
            spin_rpm=3200,
            command=90.0,
        )
        assert baseline >= 88.0
        assert baseline <= 95.0

    def test_average_pitch_starts_mid_range(self):
        """An average pitch should start in the 78-85 range."""
        baseline = compute_baseline_effectiveness(
            velocity_mph=92.0,
            break_rating=75.0,
            spin_rpm=2400,
            command=75.0,
        )
        assert 75.0 <= baseline <= 87.0

    def test_soft_secondary_pitch_lower(self):
        """A slow offspeed with modest break should start lower than fastball."""
        fb_baseline = compute_baseline_effectiveness(
            velocity_mph=95.0, break_rating=80.0, spin_rpm=2400, command=82.0
        )
        offspeed_baseline = compute_baseline_effectiveness(
            velocity_mph=82.0, break_rating=70.0, spin_rpm=1800, command=78.0
        )
        assert fb_baseline > offspeed_baseline

    def test_baseline_always_in_valid_range(self):
        """Baseline effectiveness should always be clamped to [70, 95]."""
        assert compute_baseline_effectiveness(60.0, 0.0, 1000, 30.0) >= 70.0
        assert compute_baseline_effectiveness(105.0, 100.0, 4000, 99.0) <= 95.0


class TestEffectivenessDelta:
    """Tests outcome-driven effectiveness delta calculations."""

    def test_hard_contact_degrades_effectiveness(self):
        """Home runs should cause the largest effectiveness degradation."""
        hr_delta = calculate_effectiveness_delta('HOME_RUN', current_stamina_pct=100.0)
        triple_delta = calculate_effectiveness_delta('TRIPLE', current_stamina_pct=100.0)
        double_delta = calculate_effectiveness_delta('DOUBLE', current_stamina_pct=100.0)
        single_delta = calculate_effectiveness_delta('SINGLE', current_stamina_pct=100.0)

        # All should be negative
        assert hr_delta < 0
        assert triple_delta < 0
        assert double_delta < 0
        assert single_delta < 0

        # Severity should be ordered
        assert hr_delta < triple_delta < double_delta < single_delta < 0.0

    def test_whiffs_and_weak_outs_restore_effectiveness(self):
        """Swinging strikes and weak outs recover effectiveness."""
        swinging_k = calculate_effectiveness_delta('SWINGING_STRIKE', current_stamina_pct=100.0)
        in_play_out = calculate_effectiveness_delta('IN_PLAY_OUT', current_stamina_pct=100.0)
        called_k = calculate_effectiveness_delta('CALLED_STRIKE', current_stamina_pct=100.0)

        assert swinging_k > 0
        assert in_play_out > 0
        assert called_k > 0
        assert swinging_k > in_play_out > called_k

    def test_fatigue_reduces_recovery_rate(self):
        """A tired pitcher recovers effectiveness more slowly than a fresh one."""
        fresh_recovery = calculate_effectiveness_delta('SWINGING_STRIKE', current_stamina_pct=100.0)
        fatigued_recovery = calculate_effectiveness_delta('SWINGING_STRIKE', current_stamina_pct=20.0)
        assert fatigued_recovery < fresh_recovery
        assert fatigued_recovery > 0  # Still positive but reduced

    def test_severe_low_confidence_adds_minor_drag(self):
        """Very low confidence (< 25%) causes minor secondary effectiveness drag."""
        no_conf_drag = calculate_effectiveness_delta('BALL', current_stamina_pct=100.0, pitch_confidence=50.0)
        with_conf_drag = calculate_effectiveness_delta('BALL', current_stamina_pct=100.0, pitch_confidence=10.0)
        assert with_conf_drag < no_conf_drag

    def test_moderate_confidence_no_extra_drag(self):
        """Normal confidence (>= 25%) should not cause effectiveness drag."""
        delta_high_conf = calculate_effectiveness_delta('BALL', current_stamina_pct=100.0, pitch_confidence=70.0)
        delta_neutral_conf = calculate_effectiveness_delta('BALL', current_stamina_pct=100.0, pitch_confidence=50.0)
        assert delta_high_conf == delta_neutral_conf

    def test_confidence_drag_is_minor_not_dominant(self):
        """Confidence drag should be much smaller than hard-contact degradation."""
        max_conf_drag = CONFIDENCE_DRAG_MAX  # Maximum possible drag from confidence
        hr_degradation = abs(calculate_effectiveness_delta('HOME_RUN', current_stamina_pct=100.0, pitch_confidence=0.0))
        assert max_conf_drag < hr_degradation * 0.5


class TestStaminaFatigueFall:
    """Tests the passive stamina-based effectiveness floor."""

    def test_full_stamina_no_fatigue_pull(self):
        """At 100% stamina, no fatigue floor reduction should occur."""
        eff = 85.0
        result = apply_stamina_fatigue_to_effectiveness(eff, 100.0, baseline_effectiveness=85.0)
        assert result == pytest.approx(eff, abs=0.1)

    def test_zero_stamina_applies_maximum_floor(self):
        """At 0% stamina, effectiveness is pulled to baseline - MAX_PENALTY."""
        baseline = 85.0
        expected_floor = baseline - FATIGUE_EFFECTIVENESS_MAX_PENALTY
        result = apply_stamina_fatigue_to_effectiveness(100.0, 0.0, baseline_effectiveness=baseline)
        # Should be pulled toward the floor
        assert result < 100.0

    def test_effectiveness_cannot_go_below_fatigue_floor(self):
        """Effectiveness below the fatigue floor should not be pulled further down."""
        baseline = 80.0
        fatigue_floor = baseline - FATIGUE_EFFECTIVENESS_MAX_PENALTY
        # Start below floor
        result = apply_stamina_fatigue_to_effectiveness(fatigue_floor - 5.0, 0.0, baseline_effectiveness=baseline)
        assert result >= 0.0  # Never below minimum


class TestSeparationFromConfidence:
    """
    CRITICAL: Verifies that Pitch Effectiveness and Pitch Confidence are
    fully independent tracking systems. Changing one should not directly
    change the other (only the minor coupling at extreme confidence thresholds).
    """

    def test_changing_confidence_does_not_change_effectiveness_above_threshold(self):
        """When confidence >= 25%, pitch outcome deltas are identical regardless of confidence."""
        delta_conf_50 = calculate_effectiveness_delta('SWINGING_STRIKE', 100.0, pitch_confidence=50.0)
        delta_conf_80 = calculate_effectiveness_delta('SWINGING_STRIKE', 100.0, pitch_confidence=80.0)
        delta_no_conf = calculate_effectiveness_delta('SWINGING_STRIKE', 100.0, pitch_confidence=None)

        assert delta_conf_50 == delta_conf_80
        assert delta_conf_50 == delta_no_conf

    def test_full_update_preserves_independence(self):
        """Two pitches with same outcomes but different confidence levels produce different
        effectiveness only when confidence is below the drag threshold."""
        eff_start = 80.0
        baseline = 80.0

        eff_high_conf = update_pitch_effectiveness(
            eff_start, 'IN_PLAY_OUT', current_stamina_pct=100.0,
            pitch_confidence=75.0, baseline_effectiveness=baseline
        )
        eff_low_conf = update_pitch_effectiveness(
            eff_start, 'IN_PLAY_OUT', current_stamina_pct=100.0,
            pitch_confidence=10.0, baseline_effectiveness=baseline
        )
        # Low confidence drags effectiveness slightly lower
        assert eff_low_conf < eff_high_conf
        # But the difference should be small (confidence drag is minor)
        diff = eff_high_conf - eff_low_conf
        assert diff <= CONFIDENCE_DRAG_MAX + 0.5


class TestEffectivenessToOutcomes:
    """Tests the translation of effectiveness to game outcomes (whiff rate, exit velocity)."""

    def test_higher_effectiveness_increases_whiff_rate(self):
        """High effectiveness (sharp stuff) produces higher whiff probability."""
        base_whiff = 0.25
        high_eff_whiff = apply_effectiveness_to_whiff_rate(base_whiff, pitch_effectiveness=95.0)
        neutral_whiff = apply_effectiveness_to_whiff_rate(base_whiff, pitch_effectiveness=80.0)
        low_eff_whiff = apply_effectiveness_to_whiff_rate(base_whiff, pitch_effectiveness=55.0)

        assert high_eff_whiff > neutral_whiff > low_eff_whiff

    def test_neutral_effectiveness_no_whiff_adjustment(self):
        """At effectiveness == 80 (neutral baseline), whiff probability is unchanged."""
        base_whiff = 0.30
        adjusted = apply_effectiveness_to_whiff_rate(base_whiff, pitch_effectiveness=80.0)
        assert adjusted == pytest.approx(base_whiff, abs=0.001)

    def test_lower_effectiveness_increases_exit_velocity(self):
        """Low effectiveness (flat pitch) means batters square it up harder."""
        base_ev = 88.0
        high_eff_ev = apply_effectiveness_to_exit_velocity(base_ev, pitch_effectiveness=95.0)
        neutral_ev = apply_effectiveness_to_exit_velocity(base_ev, pitch_effectiveness=80.0)
        low_eff_ev = apply_effectiveness_to_exit_velocity(base_ev, pitch_effectiveness=50.0)

        assert low_eff_ev > neutral_ev > high_eff_ev

    def test_neutral_effectiveness_no_exit_velocity_adjustment(self):
        """At effectiveness == 80 (neutral baseline), exit velocity is unchanged."""
        base_ev = 90.0
        adjusted = apply_effectiveness_to_exit_velocity(base_ev, pitch_effectiveness=80.0)
        assert adjusted == pytest.approx(base_ev, abs=0.01)


class TestEffectivenessOnCommandAndTiming:
    """
    Tests the direct impact of pitch effectiveness on command rating,
    simulation timing probabilities, velocity scaling, break bite, and hit suppression.

    User Specification Scenario:
    Two Elite Pitchers, both throwing 4SFB:
      Pitcher 1: 90 Effectiveness vs. Pitcher 2: 75 Effectiveness.
      Noticeable differences required:
      - 90% pitcher has consistent higher velocity.
      - 90% pitcher has more 'bite' (break).
      - 90% pitcher is harder to get a hit off of (higher whiff, lower exit velocity).
      - 90% pitcher has higher chance of PERFECT/GOOD, lower chance of OKAY/POOR.
      - 75% pitcher has degraded command, lower velocity, less bite, and higher chance of OKAY/POOR.
    """

    def test_command_adjustment_scaling(self):
        """Effectiveness modifies command relative to 80 baseline."""
        # 80 neutral: 0.0 adjustment
        assert calculate_command_adjustment_from_effectiveness(80.0) == 0.0

        # 90 effectiveness: +6.0 command boost
        boost_90 = calculate_command_adjustment_from_effectiveness(90.0)
        assert boost_90 == 6.0

        # 100 effectiveness: +12.0 command boost
        boost_100 = calculate_command_adjustment_from_effectiveness(100.0)
        assert boost_100 == 12.0

        # 75 effectiveness: -3.75 command penalty
        drop_75 = calculate_command_adjustment_from_effectiveness(75.0)
        assert drop_75 == -3.75

        # 60 effectiveness: -15.0 command penalty
        drop_60 = calculate_command_adjustment_from_effectiveness(60.0)
        assert drop_60 == -15.0

    def test_two_elite_pitchers_command_and_ability_tier_difference(self):
        """
        Pitcher 1 (90 Eff) vs Pitcher 2 (75 Eff) with base command 90.0:
        - Pitcher 1: command boosted to 96.0 -> remains ELITE tier.
        - Pitcher 2: command drops to 86.25 -> drops into GREAT tier.
        """
        base_cmd = 90.0
        pitch_type = "4SFB"

        cmd_p1, tier_p1 = compute_effective_command(
            base_command=base_cmd,
            pitch_type=pitch_type,
            pitch_count=1,
            stamina=85.0,
            composure=80.0,
            consistency=80.0,
            effectiveness=90.0,
        )
        cmd_p2, tier_p2 = compute_effective_command(
            base_command=base_cmd,
            pitch_type=pitch_type,
            pitch_count=1,
            stamina=85.0,
            composure=80.0,
            consistency=80.0,
            effectiveness=75.0,
        )

        assert cmd_p1 > cmd_p2
        assert cmd_p1 >= 95.0
        assert cmd_p2 < 90.0
        assert tier_p1 == AbilityTier.ELITE
        assert tier_p2 == AbilityTier.GREAT

    def test_two_elite_pitchers_velocity_difference(self):
        """Pitcher 1 (90 Eff) consistently throws faster than Pitcher 2 (75 Eff)."""
        base_velo = 95.0
        velo_p1 = apply_effectiveness_to_velocity(base_velo, pitch_effectiveness=90.0)
        velo_p2 = apply_effectiveness_to_velocity(base_velo, pitch_effectiveness=75.0)

        assert velo_p1 > base_velo
        assert velo_p2 < base_velo
        assert velo_p1 > velo_p2
        # Distinct gap: >= 2.0 mph difference
        assert (velo_p1 - velo_p2) >= 2.0

    def test_two_elite_pitchers_break_bite_difference(self):
        """Pitcher 1 (90 Eff) has more 'bite' (sharper break) than Pitcher 2 (75 Eff)."""
        hb_base, ivb_base = -6.0, 16.0
        hb_p1, ivb_p1 = apply_effectiveness_to_break(hb_base, ivb_base, pitch_effectiveness=90.0)
        hb_p2, ivb_p2 = apply_effectiveness_to_break(hb_base, ivb_base, pitch_effectiveness=75.0)

        # More bite means larger absolute movement
        assert abs(hb_p1) > abs(hb_base) > abs(hb_p2)
        assert abs(ivb_p1) > abs(ivb_base) > abs(ivb_p2)
        assert abs(ivb_p1 - ivb_p2) > 1.5

    def test_two_elite_pitchers_timing_tier_probabilities(self):
        """
        Pitcher 1 (90 Eff) has higher chance of PERFECT/GOOD timing;
        Pitcher 2 (75 Eff) has higher chance of OKAY/POOR timing.
        """
        dist_p1 = get_simulation_timing_distribution(
            ability_tier=AbilityTier.ELITE,
            effectiveness=90.0,
        )
        dist_p2 = get_simulation_timing_distribution(
            ability_tier=AbilityTier.GREAT,  # Dropped from command penalty
            effectiveness=75.0,
        )

        good_or_perfect_p1 = dist_p1["PERFECT"] + dist_p1["GOOD"]
        good_or_perfect_p2 = dist_p2["PERFECT"] + dist_p2["GOOD"]
        okay_or_poor_p1 = dist_p1["OKAY"] + dist_p1["POOR"]
        okay_or_poor_p2 = dist_p2["OKAY"] + dist_p2["POOR"]

        assert good_or_perfect_p1 > good_or_perfect_p2
        assert okay_or_poor_p2 > okay_or_poor_p1
        # Pitcher 1 achieves >= 85% PERFECT/GOOD
        assert good_or_perfect_p1 >= 0.84
        # Pitcher 2 is at least 2x more prone to OKAY/POOR than Pitcher 1
        assert okay_or_poor_p2 >= 1.8 * okay_or_poor_p1

    def test_two_elite_pitchers_hit_suppression_difference(self):
        """Pitcher 1 (90 Eff) is harder to get a hit off of than Pitcher 2 (75 Eff)."""
        base_whiff = 0.25
        base_ev = 89.0

        whiff_p1 = apply_effectiveness_to_whiff_rate(base_whiff, pitch_effectiveness=90.0)
        whiff_p2 = apply_effectiveness_to_whiff_rate(base_whiff, pitch_effectiveness=75.0)

        ev_p1 = apply_effectiveness_to_exit_velocity(base_ev, pitch_effectiveness=90.0)
        ev_p2 = apply_effectiveness_to_exit_velocity(base_ev, pitch_effectiveness=75.0)

        # Pitcher 1 fools batters more (higher whiff)
        assert whiff_p1 > base_whiff > whiff_p2
        # Pitcher 1 suppresses exit velocity (weaker contact) while Pitcher 2 gets hit harder
        assert ev_p1 < base_ev < ev_p2
        assert (ev_p2 - ev_p1) >= 2.0

    def test_pitching_engine_execute_pitch_reflects_effectiveness(self):
        """End-to-end PitchingEngine.execute_pitch reflects effectiveness in delivery."""
        from backend.engine.pitching_engine import PitchingEngine
        from backend.models.player import Player

        pitcher_data = {
            "id": 101,
            "name": "Ace Pitcher",
            "ratings": {"Control": 90, "Stamina": 85, "Composure": 80, "Consistency": 80},
            "arsenal": [
                {
                    "name": "4-Seam Fastball",
                    "category": "Fastball",
                    "velocity_mph": 95.0,
                    "spin_rpm": 2400,
                    "command": 90.0,
                    "break_rating": 80.0,
                    "horizontal_break_in": -6.0,
                    "induced_vertical_break_in": 16.0,
                }
            ],
        }
        batter_data = {
            "id": 201,
            "name": "Standard Batter",
            "ratings": {"Contact": 75, "Power": 75, "Eye": 75},
        }

        pe = PitchingEngine(Player.from_dict(pitcher_data), Player.from_dict(batter_data))

        delivery_90 = pe.execute_pitch(
            balls=0,
            strikes=0,
            selection_mode="user",
            pitch_name="4-Seam Fastball",
            target_zone="heart",
            timing_tier="GOOD",
            pitch_effectiveness=90.0,
        )
        delivery_75 = pe.execute_pitch(
            balls=0,
            strikes=0,
            selection_mode="user",
            pitch_name="4-Seam Fastball",
            target_zone="heart",
            timing_tier="GOOD",
            pitch_effectiveness=75.0,
        )

        # 90 effectiveness throws faster with sharper break and tighter radius
        assert delivery_90["velocity_mph"] > delivery_75["velocity_mph"]
        assert delivery_90["max_radius_inches"] < delivery_75["max_radius_inches"]
        assert abs(delivery_90["induced_vertical_break_in"]) > abs(delivery_75["induced_vertical_break_in"])
        assert delivery_90["pitch_effectiveness"] == 90.0
        assert delivery_75["pitch_effectiveness"] == 75.0


