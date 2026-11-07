"""
Adversarial Stress Test Suite for Milestone 1: Pitcher Ability Tiers & Rating Logic.
Authored by: teamwork_challenger (empirical verification).

Validates:
1. Exact boundary transitions for get_ability_tier across all 6 tiers (ELITE, GREAT, GOOD, OKAY, MEDIOCRE, POOR).
2. Clamping behavior under extreme inputs (negative rating, zero, 150.0, 999.0).
3. Extreme fatigue behavior (0 stamina, 200 pitch count, negative pitch count, excessive fatigue_pct).
4. Pitch type difficulty degradation (KN 1.35x vs 4SFB 1.00x, alias normalization, fallback handling).
5. Exact TIMING_MULTIPLIERS calibration (PERFECT 0.52, GOOD 1.00, OKAY 1.97, POOR 3.75).
6. InGamePitcherRatings and PitcherInstanceManager robustness, schema compliance, and immutability.
"""

import math
import pytest
from tiers import (
    AbilityTier,
    TimingTier,
    TIMING_MULTIPLIERS,
    PITCH_TYPE_MODIFIERS,
    PITCH_TYPE_ALIASES,
    get_ability_tier,
    get_pitch_type_modifier,
)
from backend.engine.pitching_engine.pitcher_info.adjusted_ratings import (
    compute_effective_command,
    InGamePitcherRatings,
    PitchArsenalMetrics,
    PitcherInstanceManager,
    evaluate_pitch_arsenal,
)


# ============================================================================
# 1. Exact Boundary Transitions
# ============================================================================

class TestBoundaryTransitions:
    """Stress tests boundary transitions between all adjacent ability tiers."""

    @pytest.mark.parametrize(
        "effective_cmd,expected_tier",
        [
            # ELITE vs GREAT (90.00 boundary)
            (90.000, AbilityTier.ELITE),
            (90.001, AbilityTier.ELITE),
            (89.999, AbilityTier.GREAT),
            (89.999999, AbilityTier.GREAT),
            (89.99, AbilityTier.GREAT),
            
            # GREAT vs GOOD (80.00 boundary)
            (80.000, AbilityTier.GREAT),
            (80.001, AbilityTier.GREAT),
            (79.999, AbilityTier.GOOD),
            (79.999999, AbilityTier.GOOD),
            (79.99, AbilityTier.GOOD),

            # GOOD vs OKAY (70.00 boundary)
            (70.000, AbilityTier.GOOD),
            (70.001, AbilityTier.GOOD),
            (69.999, AbilityTier.OKAY),
            (69.999999, AbilityTier.OKAY),
            (69.99, AbilityTier.OKAY),

            # OKAY vs MEDIOCRE (60.00 boundary)
            (60.000, AbilityTier.OKAY),
            (60.001, AbilityTier.OKAY),
            (59.999, AbilityTier.MEDIOCRE),
            (59.999999, AbilityTier.MEDIOCRE),
            (59.99, AbilityTier.MEDIOCRE),

            # MEDIOCRE vs POOR (50.00 boundary)
            (50.000, AbilityTier.MEDIOCRE),
            (50.001, AbilityTier.MEDIOCRE),
            (49.999, AbilityTier.POOR),
            (49.999999, AbilityTier.POOR),
            (49.99, AbilityTier.POOR),
        ],
    )
    def test_get_ability_tier_exact_boundaries(self, effective_cmd, expected_tier):
        actual = get_ability_tier(effective_cmd)
        assert actual == expected_tier, (
            f"Expected get_ability_tier({effective_cmd}) to be {expected_tier}, got {actual}"
        )

    def test_compute_effective_command_boundary_rounding(self):
        """Verify compute_effective_command handles boundary rounding and tier assignment cleanly."""
        # Clean 90.00
        cmd, tier = compute_effective_command(
            base_command=90.0,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=80.0,
            composure=80.0,
            consistency=80.0,
            is_leverage=False,
        )
        assert cmd == 90.0
        assert tier == AbilityTier.ELITE

        # 89.99 base command
        cmd, tier = compute_effective_command(
            base_command=89.99,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=80.0,
            composure=80.0,
            consistency=80.0,
            is_leverage=False,
        )
        assert cmd == 89.99
        assert tier == AbilityTier.GREAT

        # 80.00 base command
        cmd, tier = compute_effective_command(
            base_command=80.0,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=80.0,
            composure=80.0,
            consistency=80.0,
            is_leverage=False,
        )
        assert cmd == 80.0
        assert tier == AbilityTier.GREAT

        # 79.99 base command
        cmd, tier = compute_effective_command(
            base_command=79.99,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=80.0,
            composure=80.0,
            consistency=80.0,
            is_leverage=False,
        )
        assert cmd == 79.99
        assert tier == AbilityTier.GOOD

        # 50.00 base command
        cmd, tier = compute_effective_command(
            base_command=50.0,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=80.0,
            composure=80.0,
            consistency=80.0,
            is_leverage=False,
        )
        assert cmd == 50.0
        assert tier == AbilityTier.MEDIOCRE

        # 49.99 base command
        cmd, tier = compute_effective_command(
            base_command=49.99,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=80.0,
            composure=80.0,
            consistency=80.0,
            is_leverage=False,
        )
        assert cmd == 49.99
        assert tier == AbilityTier.POOR


# ============================================================================
# 2. Extreme Inputs & Clamping
# ============================================================================

class TestExtremeInputsClamping:
    """Stress tests boundary clamps [30.0, 99.0] under pathological inputs."""

    @pytest.mark.parametrize(
        "extreme_base_cmd,expected_clamped_cmd,expected_tier",
        [
            (-100.0, 30.0, AbilityTier.POOR),
            (-1.0, 30.0, AbilityTier.POOR),
            (0.0, 30.0, AbilityTier.POOR),
            (10.0, 30.0, AbilityTier.POOR),
            (29.99, 30.0, AbilityTier.POOR),
            (30.0, 30.0, AbilityTier.POOR),
            (99.0, 99.0, AbilityTier.ELITE),
            (99.01, 99.0, AbilityTier.ELITE),
            (105.0, 99.0, AbilityTier.ELITE),
            (150.0, 99.0, AbilityTier.ELITE),
            (999.0, 99.0, AbilityTier.ELITE),
        ],
    )
    def test_command_clamping(self, extreme_base_cmd, expected_clamped_cmd, expected_tier):
        cmd, tier = compute_effective_command(
            base_command=extreme_base_cmd,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=75.0,
            composure=75.0,
            consistency=75.0,
            is_leverage=False,
        )
        assert cmd == expected_clamped_cmd, (
            f"Expected {extreme_base_cmd} to clamp to {expected_clamped_cmd}, got {cmd}"
        )
        assert tier == expected_tier

    def test_extreme_composure_and_consistency(self):
        """Test pathological composure/consistency values under high leverage."""
        # 0 composure and 0 consistency (maximum possible panic penalty)
        cmd, tier = compute_effective_command(
            base_command=80.0,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=75.0,
            composure=0.0,
            consistency=0.0,
            is_leverage=True,
        )
        # comp_scale = (100 - 0)/100 = 1.0; cons_dampener = 1.0 - 0 = 1.0; penalty = 10.0 * 1.0 * 1.0 = 10.0
        assert math.isclose(cmd, 70.0, abs_tol=0.01)
        assert tier == AbilityTier.GOOD

        # 100 composure (completely immune to leverage stress)
        cmd_ice, tier_ice = compute_effective_command(
            base_command=80.0,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=75.0,
            composure=100.0,
            consistency=50.0,
            is_leverage=True,
        )
        # comp_scale = 0.0 -> penalty = 0.0
        assert math.isclose(cmd_ice, 80.0, abs_tol=0.01)
        assert tier_ice == AbilityTier.GREAT

        # Negative composure & negative consistency
        cmd_neg, tier_neg = compute_effective_command(
            base_command=50.0,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=75.0,
            composure=-50.0,
            consistency=-50.0,
            is_leverage=True,
        )
        # Must still clamp to >= 30.0 and never fail
        assert cmd_neg >= 30.0
        assert tier_neg == AbilityTier.POOR

        # Hyper-high composure (>100)
        cmd_high, tier_high = compute_effective_command(
            base_command=80.0,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=75.0,
            composure=150.0,
            consistency=150.0,
            is_leverage=True,
        )
        # comp_scale is clamped to max(0.0, ...), penalty is 0, no bonus inflation beyond base
        assert cmd_high == 80.0
        assert tier_high == AbilityTier.GREAT


# ============================================================================
# 3. Fatigue & Stamina Stress Testing
# ============================================================================

class TestFatigueStaminaStress:
    """Stress tests fatigue degradation under pathological pitch counts and stamina."""

    def test_zero_and_negative_stamina(self):
        """Verify 0 stamina or negative stamina does not cause ZeroDivisionError and applies max fatigue decay."""
        # 0 stamina with 200 pitch count
        cmd, tier = compute_effective_command(
            base_command=80.0,
            pitch_type="4SFB",
            pitch_count=200,
            stamina=0.0,
            composure=75.0,
            consistency=75.0,
            is_leverage=False,
        )
        # Max fatigue decay is 10.0 points -> 80.0 - 10.0 = 70.0
        assert math.isclose(cmd, 70.0, abs_tol=0.01)
        assert tier == AbilityTier.GOOD

        # Negative stamina (-50.0) with 200 pitch count
        cmd_neg, _ = compute_effective_command(
            base_command=80.0,
            pitch_type="4SFB",
            pitch_count=200,
            stamina=-50.0,
            composure=75.0,
            consistency=75.0,
            is_leverage=False,
        )
        assert math.isclose(cmd_neg, 70.0, abs_tol=0.01)

    def test_negative_pitch_count(self):
        """Negative pitch count should apply 0 fatigue decay."""
        cmd, _ = compute_effective_command(
            base_command=80.0,
            pitch_type="4SFB",
            pitch_count=-25,
            stamina=75.0,
            composure=75.0,
            consistency=75.0,
            is_leverage=False,
        )
        assert cmd == 80.0

    def test_extreme_pitch_count_capped_at_max_decay(self):
        """Even 500 pitches should cap fatigue decay at 10.0 points."""
        cmd, _ = compute_effective_command(
            base_command=85.0,
            pitch_type="4SFB",
            pitch_count=500,
            stamina=75.0,
            composure=75.0,
            consistency=75.0,
            is_leverage=False,
        )
        assert math.isclose(cmd, 75.0, abs_tol=0.01)

    def test_explicit_fatigue_pct(self):
        """Explicit fatigue_pct parameter takes precedence and is bounded [0, 100]."""
        # 0% fatigue
        cmd_0, _ = compute_effective_command(
            base_command=85.0,
            pitch_type="4SFB",
            pitch_count=100,  # Ignored when fatigue_pct passed
            stamina=75.0,
            composure=75.0,
            consistency=75.0,
            is_leverage=False,
            fatigue_pct=0.0,
        )
        assert cmd_0 == 85.0

        # 50% fatigue -> 10.0 point decay
        cmd_50, _ = compute_effective_command(
            base_command=85.0,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=75.0,
            composure=75.0,
            consistency=75.0,
            is_leverage=False,
            fatigue_pct=50.0,
        )
        assert math.isclose(cmd_50, 75.0, abs_tol=0.01)

        # 150% fatigue (extreme) -> capped at 10.0 point decay
        cmd_150, _ = compute_effective_command(
            base_command=85.0,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=75.0,
            composure=75.0,
            consistency=75.0,
            is_leverage=False,
            fatigue_pct=150.0,
        )
        assert math.isclose(cmd_150, 75.0, abs_tol=0.01)

        # -50% fatigue (pathological) -> treated as 0% fatigue
        cmd_neg, _ = compute_effective_command(
            base_command=85.0,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=75.0,
            composure=75.0,
            consistency=75.0,
            is_leverage=False,
            fatigue_pct=-50.0,
        )
        assert cmd_neg == 85.0


# ============================================================================
# 4. Pitch Type Degradation Stress Testing
# ============================================================================

class TestPitchTypeDegradation:
    """Stress tests pitch type difficulty modifiers and degradation curves."""

    def test_knuckleball_vs_4sfb_exact_ratio(self):
        """Knuckleball (1.35x) degrades command by exactly 1.35x divisor relative to 4SFB (1.00x)."""
        base_cmd = 90.0
        cmd_4sfb, tier_4sfb = compute_effective_command(
            base_command=base_cmd,
            pitch_type="4SFB",
            pitch_count=0,
            stamina=80.0,
            composure=80.0,
            consistency=80.0,
        )
        cmd_kn, tier_kn = compute_effective_command(
            base_command=base_cmd,
            pitch_type="KN",
            pitch_count=0,
            stamina=80.0,
            composure=80.0,
            consistency=80.0,
        )

        assert cmd_4sfb == 90.0
        assert tier_4sfb == AbilityTier.ELITE

        # 90.0 - (1.35 - 1.0) * 20.0 = 83.0
        assert cmd_kn == 83.0
        assert tier_kn == AbilityTier.GREAT

        # Degradation penalty is 7.0 command points
        penalty = cmd_4sfb - cmd_kn
        assert math.isclose(penalty, 7.0, rel_tol=1e-3)

    def test_all_pitch_type_modifiers_order(self):
        """Verify monotonic difficulty degradation across standard repertoire types."""
        pitches_ordered = [
            ("4SFB", 1.00),
            ("2SFB", 1.02),
            ("CUT", 1.05),
            ("SNK", 1.05),
            ("CH", 1.08),
            ("SL", 1.15),
            ("SWP", 1.18),
            ("CB", 1.20),
            ("SPL", 1.25),
            ("KN", 1.35),
        ]
        base_cmd = 90.0
        prev_effective = 100.0

        for pitch_code, expected_mod in pitches_ordered:
            mod = get_pitch_type_modifier(pitch_code)
            assert math.isclose(mod, expected_mod, rel_tol=1e-3)

            eff_cmd, _ = compute_effective_command(
                base_command=base_cmd,
                pitch_type=pitch_code,
                pitch_count=0,
                stamina=80.0,
                composure=80.0,
                consistency=80.0,
            )
            assert eff_cmd <= prev_effective + 1e-4, (
                f"Pitch {pitch_code} effective {eff_cmd} not monotonically non-increasing"
            )
            prev_effective = eff_cmd

    def test_pitch_type_aliases_and_case_insensitivity(self):
        """Verify aliases and case/whitespace variations resolve to correct modifiers."""
        variations = [
            ("4-seam fastball", 1.00),
            ("FOUR-SEAM FASTBALL", 1.00),
            ("  slider  ", 1.15),
            ("Slider", 1.15),
            ("CIRCLE CHANGEUP", 1.08),
            ("Knuckleball", 1.35),
            ("KNUCKLEBALL", 1.35),
            ("Curveball", 1.20),
            ("SPIKE CURVEBALL", 1.20),
            ("Splitter", 1.25),
            ("GHOST FORK", 1.25),
            ("Power Sinker", 1.05),
            ("SI", 1.05),
            ("SWEEPER", 1.18),
        ]
        for name, expected_mod in variations:
            mod = get_pitch_type_modifier(name)
            assert math.isclose(mod, expected_mod, rel_tol=1e-3), (
                f"Failed for alias '{name}': expected {expected_mod}, got {mod}"
            )

    def test_unknown_and_empty_pitch_type_fallback(self):
        """Unknown or empty pitch types must safely fall back to 1.00 modifier without crashing."""
        for invalid in ["", "   ", "Gyroball", "EEPHUS_CUSTOM_XYZ", None]:
            mod = get_pitch_type_modifier(invalid)
            assert mod == 1.00, f"Expected 1.00 fallback for '{invalid}', got {mod}"
            cmd, _ = compute_effective_command(
                base_command=75.0,
                pitch_type=invalid,
                pitch_count=0,
                stamina=75.0,
                composure=75.0,
                consistency=75.0,
            )
            assert cmd == 75.0


# ============================================================================
# 5. Timing Multipliers Verification
# ============================================================================

class TestTimingMultipliers:
    """Stress tests TIMING_MULTIPLIERS calibrated values and enum integrity."""

    def test_timing_multipliers_exact_values(self):
        """Verify exact specified multipliers: PERFECT=0.52, GOOD=1.00, OKAY=1.97, POOR=3.75."""
        assert math.isclose(TIMING_MULTIPLIERS[TimingTier.PERFECT], 0.52, rel_tol=1e-4)
        assert math.isclose(TIMING_MULTIPLIERS[TimingTier.GOOD], 1.00, rel_tol=1e-4)
        assert math.isclose(TIMING_MULTIPLIERS[TimingTier.OKAY], 1.97, rel_tol=1e-4)
        assert math.isclose(TIMING_MULTIPLIERS[TimingTier.POOR], 3.75, rel_tol=1e-4)

    def test_timing_tiers_complete_and_exclusive(self):
        """Verify exactly 4 timing tiers exist with string values matching names."""
        assert len(TimingTier) == 4
        expected = {"PERFECT": 0.52, "GOOD": 1.00, "OKAY": 1.97, "POOR": 3.75}
        for name, expected_val in expected.items():
            assert name in TimingTier.__members__
            tier = TimingTier[name]
            assert tier.value == name
            assert TIMING_MULTIPLIERS[tier] == expected_val

    def test_timing_ordering_progression(self):
        """Timing multipliers must strictly scale error: PERFECT < GOOD < OKAY < POOR."""
        assert (
            TIMING_MULTIPLIERS[TimingTier.PERFECT]
            < TIMING_MULTIPLIERS[TimingTier.GOOD]
            < TIMING_MULTIPLIERS[TimingTier.OKAY]
            < TIMING_MULTIPLIERS[TimingTier.POOR]
        )


# ============================================================================
# 6. InGamePitcherRatings & evaluate_pitch_arsenal Immutability
# ============================================================================

class TestInGamePitcherRatingsAndArsenal:
    """Tests InGamePitcherRatings and evaluate_pitch_arsenal robustness and immutability."""

    def test_ingame_pitcher_ratings_defaults_and_to_dict(self):
        """InGamePitcherRatings to_dict exports all required fields."""
        ratings = InGamePitcherRatings(
            pitcher_id=42,
            pitcher_name="Ace Test",
            base_command=85.0,
            base_stamina=80.0,
            base_velocity=96.0,
            base_break=88.0,
            effective_command=85.0,
            base_composure=82.0,
            consistency=78.0,
            is_leverage=True,
        )
        d = ratings.to_dict()
        assert d["pitcher_id"] == 42
        assert d["pitcher_name"] == "Ace Test"
        assert d["base_command"] == 85.0
        assert d["base_composure"] == 82.0
        assert d["consistency"] == 78.0
        assert d["is_leverage"] is True

    def test_evaluate_pitch_arsenal_immutability(self):
        """Arsenal evaluation must never mutate input dicts or domain player arsenals."""
        original_pitch = {
            "name": "4-Seam Fastball",
            "id": "4SFB",
            "category": "Fastball",
            "control": 82.0,
            "velocity_mph": 95.0,
            "spin_rpm": 2350,
            "max_radius_inches": 1.55,
            "sigma": 0.045,
        }
        pitcher = {
            "id": 99,
            "name": "Test Pitcher",
            "stamina": 75.0,
            "composure": 80.0,
            "consistency": 75.0,
            "ratings": {"Control": 82.0},
            "pitch_arsenal": [original_pitch],
        }

        arsenal_metrics = evaluate_pitch_arsenal(pitcher)
        assert "4-Seam Fastball" in arsenal_metrics
        metric = arsenal_metrics["4-Seam Fastball"]

        assert isinstance(metric, PitchArsenalMetrics)
        assert metric.ability_tier == AbilityTier.GREAT
        assert metric.effective_command == 82.0

        # Verify original pitch dict was not mutated
        assert original_pitch["control"] == 82.0
        assert "ability_tier" not in original_pitch

        # Verify to_dict output format
        metric_dict = metric.to_dict()
        assert metric_dict["ability_tier"] == "GREAT"
        assert metric_dict["command"] == 82.0
        assert metric_dict["effective_command"] == 82.0

    def test_empty_arsenal_handling(self):
        """Pitcher with empty or missing arsenal returns empty dict without errors."""
        assert evaluate_pitch_arsenal(None) == {}
        assert evaluate_pitch_arsenal({"pitch_arsenal": []}) == {}
