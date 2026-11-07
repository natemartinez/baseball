"""
Adversarial Stress Test Suite for Milestone 2:
Radius Scaling, Simulation Probability Distributions & Directional Dispersion.
Authored by: teamwork_challenger (empirical verification).

Validates:
1. Directional tendencies verification:
   - PERFECT timing: 5,000 points. Mean radial miss E[r] < 0.45 * R_exec (tight center clustering).
   - GOOD timing: 5,000 points. Uniform area distribution (mean radial miss ≈ 2/3 * R_exec).
   - Early release RHP: 5,000 points. Misses sail high (+Z > 0) and arm-side (-X < 0).
   - Early release LHP: 5,000 points. Arm-side polarity flips horizontally (+X > 0, +Z > 0).
   - Late release: 5,000 points. Downward dirt spike (-Z < 0, centered near 270 deg).
2. Hard boundary circle guarantee:
   - 100% of realized misses satisfy r <= R_exec.
   - Surfaces boundary leakage and coordinate teleportation bugs in calculate_pitch_delivery.
3. Distribution stress tests:
   - Extreme composure and fatigue distribution invariant sum = 1.0.
   - Extreme ratings and non-mutation checks.
"""

import math
import random
import pytest

from tiers import (
    TimingTier,
    AbilityTier,
    TIMING_MULTIPLIERS,
    BASELINE_TIMING_PROBABILITIES,
    get_ability_tier,
)
from backend.engine.game_engine.gameday_math import (
    get_max_error_radius_inches,
    get_executed_radius_inches,
    sample_directional_dispersion,
    is_rulebook_strike,
    get_zone_nominal_target,
)
from backend.engine.pitching_engine.pitch_execution.calculations import (
    calculate_pitch_delivery,
    get_simulation_timing_distribution,
    sample_simulation_timing_tier,
    roll_simulation_timing,
)


# ============================================================================
# 1. Empirical Directional Tendencies (5,000+ Samples Each)
# ============================================================================

class TestDirectionalTendenciesEmpirical:
    """Empirically stress-tests directional dispersion across 5,000 samples per condition."""

    def test_perfect_timing_tight_center_clustering_5000_samples(self):
        """PERFECT timing: 5,000 samples. Verify E[r] < 0.45 * R_exec and 0 leakage."""
        rng = random.Random(42)
        r_exec = 2.50  # inches
        n_samples = 5000
        radial_misses = []

        for _ in range(n_samples):
            dx, dz, r = sample_directional_dispersion(
                executed_radius_inches=r_exec,
                timing_tier=TimingTier.PERFECT,
                rng=rng,
            )
            assert r <= r_exec + 1e-9, f"Radial miss {r} exceeded R_exec {r_exec}"
            radial_misses.append(r)

        mean_r = sum(radial_misses) / len(radial_misses)
        ratio = mean_r / r_exec

        # Folded normal with sigma=0.35 has theoretical mean ~0.279
        assert ratio < 0.45, f"PERFECT mean radial ratio {ratio:.4f} exceeds 0.45 limit"
        assert math.isclose(ratio, 0.279, abs_tol=0.03), f"PERFECT mean ratio {ratio:.4f} deviated from theory"

    def test_good_timing_uniform_area_distribution_5000_samples(self):
        """GOOD timing: 5,000 samples. Verify uniform area distribution (E[r] ≈ 2/3 * R_exec)."""
        rng = random.Random(1337)
        r_exec = 3.00  # inches
        n_samples = 5000
        radial_misses = []
        quadrants = [0, 0, 0, 0]  # Q1 (+,+), Q2 (-,+), Q3 (-,-), Q4 (+,-)

        for _ in range(n_samples):
            dx, dz, r = sample_directional_dispersion(
                executed_radius_inches=r_exec,
                timing_tier=TimingTier.GOOD,
                rng=rng,
            )
            assert r <= r_exec + 1e-9, f"Radial miss {r} exceeded R_exec {r_exec}"
            radial_misses.append(r)

            if dx >= 0 and dz >= 0:
                quadrants[0] += 1
            elif dx < 0 and dz >= 0:
                quadrants[1] += 1
            elif dx < 0 and dz < 0:
                quadrants[2] += 1
            else:
                quadrants[3] += 1

        mean_r = sum(radial_misses) / len(radial_misses)
        ratio = mean_r / r_exec
        expected_ratio = 2.0 / 3.0  # 0.6667 for 2D circular uniform area distribution

        assert math.isclose(ratio, expected_ratio, abs_tol=0.03), (
            f"GOOD mean radial ratio {ratio:.4f} deviated from theoretical 2/3 ({expected_ratio:.4f})"
        )

        # Verify isotropic quadrant balance: each quadrant must receive ~25% ± 4%
        for i, count in enumerate(quadrants):
            pct = count / n_samples
            assert 0.21 <= pct <= 0.29, f"Quadrant {i+1} count {count} ({pct:.1%}) deviated from isotropic uniformity"

    def test_early_release_rhp_directional_bias_5000_samples(self):
        """Early release RHP: 5,000 samples. Verify 100% misses sail high (+Z > 0) and arm-side (-X < 0)."""
        rng = random.Random(999)
        r_exec = 4.00
        n_samples = 5000
        high_arm_count = 0

        for _ in range(n_samples):
            dx, dz, r = sample_directional_dispersion(
                executed_radius_inches=r_exec,
                timing_tier=TimingTier.OKAY,
                pitcher_hand="R",
                timing_label="EARLY • OKAY",
                rng=rng,
            )
            assert r <= r_exec + 1e-9
            if dx < 0 and dz > 0:
                high_arm_count += 1

        assert high_arm_count == n_samples, (
            f"Expected 100% of Early RHP misses in (-X, +Z) quadrant, got {high_arm_count}/{n_samples}"
        )

    def test_early_release_lhp_polarity_flip_5000_samples(self):
        """Early release LHP: 5,000 samples. Verify arm-side polarity flips horizontally (+X > 0, +Z > 0)."""
        rng = random.Random(888)
        r_exec = 4.00
        n_samples = 5000
        high_arm_count = 0

        for _ in range(n_samples):
            dx, dz, r = sample_directional_dispersion(
                executed_radius_inches=r_exec,
                timing_tier=TimingTier.POOR,
                pitcher_hand="L",
                timing_label="EARLY • POOR",
                rng=rng,
            )
            assert r <= r_exec + 1e-9
            if dx > 0 and dz > 0:
                high_arm_count += 1

        assert high_arm_count == n_samples, (
            f"Expected 100% of Early LHP misses in (+X, +Z) quadrant, got {high_arm_count}/{n_samples}"
        )

    def test_late_release_dirt_spike_5000_samples(self):
        """Late release: 5,000 samples. Verify downward dirt spike (-Z < 0, centered near 270 deg)."""
        rng = random.Random(777)
        r_exec = 5.00
        n_samples = 5000
        dirt_count = 0
        angles = []

        for _ in range(n_samples):
            dx, dz, r = sample_directional_dispersion(
                executed_radius_inches=r_exec,
                timing_tier=TimingTier.POOR,
                pitcher_hand="R",
                timing_label="LATE • POOR",
                rng=rng,
            )
            assert r <= r_exec + 1e-9
            if dz < 0:
                dirt_count += 1
            ang = math.degrees(math.atan2(dz, dx)) % 360
            angles.append(ang)

        assert dirt_count == n_samples, (
            f"Expected 100% of Late misses to spike downward (-Z < 0), got {dirt_count}/{n_samples}"
        )
        mean_angle = sum(angles) / len(angles)
        assert math.isclose(mean_angle, 270.0, abs_tol=2.0), (
            f"Late release mean angle {mean_angle:.2f} deg deviated from 270 deg (straight down)"
        )


# ============================================================================
# 2. Hard Boundary Circle Verification & Bug Exposure
# ============================================================================

class TestHardBoundaryCircleEmpirical:
    """Stress-tests the hard error radius boundary circle guarantee."""

    def test_sample_directional_dispersion_zero_leakage_100k(self):
        """Direct 100,000 call Monte Carlo on sample_directional_dispersion guarantees zero leakage."""
        rng = random.Random(2026)
        tiers = [TimingTier.PERFECT, TimingTier.GOOD, TimingTier.OKAY, TimingTier.POOR]
        labels = [None, "PERFECT!", "GOOD", "EARLY • OKAY", "LATE • OKAY", "EARLY • POOR", "LATE • POOR"]
        hands = ["R", "L"]

        for _ in range(100000):
            t = random.choice(tiers)
            l = random.choice(labels)
            h = random.choice(hands)
            R = random.uniform(0.5, 25.0)

            dx, dz, r = sample_directional_dispersion(
                executed_radius_inches=R,
                timing_tier=t,
                pitcher_hand=h,
                timing_label=l,
                rng=rng,
            )
            hypot_r = math.hypot(dx, dz)
            assert r <= R + 1e-12, f"Leaked: r={r} > R={R}"
            assert hypot_r <= R + 1e-12, f"Leaked: hypot={hypot_r} > R={R}"

    def test_calculate_pitch_delivery_chase_center_teleportation_leak(self):
        """
        CRITICAL VULNERABILITY CHECK:
        If target is center (0.0, 2.50) with ELITE command (99.0) and PERFECT timing,
        but intended_zone_cat is passed as 'CHASE', calculate_pitch_delivery must NOT
        teleport realized_z to the dirt (1.4999 ft) and explode radial miss to 12.00 inches.
        """
        delivery = calculate_pitch_delivery(
            target_x=0.0,
            target_z=2.50,
            command_rating=99.0,
            pitch_count=10,
            stamina=80.0,
            intended_zone_cat="CHASE",
            timing_tier=TimingTier.PERFECT,
            timing_label="PERFECT!",
        )

        r_exec = delivery["executed_radius_inches"]
        r_miss = delivery["radial_miss_inches"]
        rx = delivery["realized_x"]
        rz = delivery["realized_z"]

        # This assertion exposes the bug in calculations.py lines 371-380
        assert r_miss <= r_exec + 1e-4, (
            f"BOUNDARY BLOWOUT: r_miss={r_miss:.4f}\" exceeded r_exec={r_exec:.4f}\" "
            f"by {r_miss - r_exec:.4f}\" (realized landing teleported to rx={rx:.4f}, rz={rz:.4f})"
        )

    def test_calculate_pitch_delivery_chase_in_horizontal_leak(self):
        """
        CRITICAL VULNERABILITY CHECK:
        If target is chase-in (-1.05, 2.50) with command 82.0 and POOR timing,
        horizontal arm-side penetration into the rulebook zone must NOT cause vertical
        teleportation of realized_z to 3.5001 ft, blowing radial miss to ~12.96\" vs executed radius 5.625\".
        """
        rng = random.Random(42)
        delivery = calculate_pitch_delivery(
            target_x=-1.05,
            target_z=2.50,
            command_rating=82.0,
            pitch_count=0,
            stamina=70.0,
            intended_zone_cat="CHASE",
            timing_tier=TimingTier.POOR,
            timing_label="EARLY • POOR",
            pitcher_hand="L",
            rng=rng,
        )

        r_exec = delivery["executed_radius_inches"]
        r_miss = delivery["radial_miss_inches"]
        rx = delivery["realized_x"]
        rz = delivery["realized_z"]

        assert r_miss <= r_exec + 1e-4, (
            f"BOUNDARY BLOWOUT on chase-in: r_miss={r_miss:.4f}\" exceeded r_exec={r_exec:.4f}\" "
            f"(realized landing teleported to rx={rx:.4f}, rz={rz:.4f})"
        )


# ============================================================================
# 3. Dynamic Simulation Distribution Invariants Under Stress
# ============================================================================

class TestSimulationDistributionInvariants:
    """Stress-tests mathematical invariants of the dynamic simulation timing distribution."""

    @pytest.mark.parametrize("ability_tier", ["ELITE", "GREAT", "GOOD", "OKAY", "MEDIOCRE", "POOR"])
    def test_distribution_sum_exact_unity(self, ability_tier):
        """Timing distribution must sum to exactly 1.0 across all tiers and stress levels."""
        for comp in [0.0, 25.0, 50.0, 75.0, 100.0]:
            for cons in [0.0, 25.0, 50.0, 75.0, 100.0]:
                for pc in [0, 50, 100, 150]:
                    for lev in [True, False]:
                        dist = get_simulation_timing_distribution(
                            ability_tier=ability_tier,
                            composure=comp,
                            consistency=cons,
                            pitch_count=pc,
                            stamina=65.0,
                            is_leverage=lev,
                        )
                        total = sum(dist.values())
                        assert math.isclose(total, 1.00, abs_tol=1e-5), (
                            f"Sum {total} != 1.0 for {ability_tier}, comp={comp}, cons={cons}, pc={pc}, lev={lev}"
                        )
                        for k, v in dist.items():
                            assert 0.0 <= v <= 1.0, f"Probability {k}={v} out of bounds [0, 1]"
