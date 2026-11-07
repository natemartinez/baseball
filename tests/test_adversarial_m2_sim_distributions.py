"""
Adversarial & Empirical Stress Test Suite for Milestone 2: Simulation Probability Distributions & Tiers.
Authored by: teamwork_challenger (empirical verification).

Validates:
1. Monte Carlo simulation test across all 6 ability tiers (N = 10,000 rolls per tier).
   Empirical frequencies must match the baseline table within 3-sigma binomial confidence intervals:
   - Elite: 45% Perfect, 45% Good, 8% Okay, 2% Poor
   - Great: 35% Perfect, 48% Good, 14% Okay, 3% Poor
   - Good: 25% Perfect, 50% Good, 20% Okay, 5% Poor
   - Okay: 15% Perfect, 45% Good, 30% Okay, 10% Poor
   - Mediocre: 8% Perfect, 37% Good, 37% Okay, 18% Poor
   - Poor: 5% Perfect, 30% Good, 40% Okay, 25% Poor
2. Dynamic modifier shifts:
   - Fatigue shift (fatigue_pct = 80%) shifts probabilities towards OKAY and POOR.
   - Leverage stress (is_leverage=True, low composure) shifts probabilities towards OKAY and POOR.
   - Consistency dampens this shift and suppresses collapse into POOR.
3. Extreme boundary inputs & probability invariants:
   - Clamping and graceful handling of out-of-range ratings (<0, >100, stamina=0).
   - Distribution sums exactly to 1.0000 across all edge cases.
4. End-to-end simulation delivery telemetry and zero leakage guarantee.
"""

import math
import random
import pytest

from tiers import (
    AbilityTier,
    TimingTier,
    TIMING_MULTIPLIERS,
    BASELINE_TIMING_PROBABILITIES,
)
from backend.engine.pitching_engine.pitch_execution.calculations import (
    get_simulation_timing_distribution,
    sample_simulation_timing_tier,
    roll_simulation_timing,
    calculate_pitch_delivery,
)


# ============================================================================
# 1. Monte Carlo Simulation Empirical Tests (N = 10,000 per tier, 3-sigma)
# ============================================================================

class TestMonteCarloSimulationTiming:
    """Rigorous empirical verification of simulation timing roll distributions."""

    ALL_TIERS = [
        AbilityTier.ELITE,
        AbilityTier.GREAT,
        AbilityTier.GOOD,
        AbilityTier.OKAY,
        AbilityTier.MEDIOCRE,
        AbilityTier.POOR,
    ]

    EXPECTED_BASELINES = {
        AbilityTier.ELITE: {"PERFECT": 0.45, "GOOD": 0.45, "OKAY": 0.08, "POOR": 0.02},
        AbilityTier.GREAT: {"PERFECT": 0.35, "GOOD": 0.48, "OKAY": 0.14, "POOR": 0.03},
        AbilityTier.GOOD: {"PERFECT": 0.25, "GOOD": 0.50, "OKAY": 0.20, "POOR": 0.05},
        AbilityTier.OKAY: {"PERFECT": 0.15, "GOOD": 0.45, "OKAY": 0.30, "POOR": 0.10},
        AbilityTier.MEDIOCRE: {"PERFECT": 0.08, "GOOD": 0.37, "OKAY": 0.37, "POOR": 0.18},
        AbilityTier.POOR: {"PERFECT": 0.05, "GOOD": 0.30, "OKAY": 0.40, "POOR": 0.25},
    }

    @pytest.mark.parametrize("tier", ALL_TIERS)
    def test_monte_carlo_10k_rolls_within_3sigma(self, tier):
        """Empirically test 10,000 rolls per tier and verify all 4 timings match baseline within 3-sigma."""
        n_samples = 10000
        rng = random.Random(42 + hash(tier.value) % 1000)

        counts = {"PERFECT": 0, "GOOD": 0, "OKAY": 0, "POOR": 0}
        for _ in range(n_samples):
            rolled = sample_simulation_timing_tier(tier, rng=rng)
            tier_str = rolled.value if hasattr(rolled, "value") else str(rolled)
            counts[tier_str] += 1

        expected = self.EXPECTED_BASELINES[tier]
        for key in ["PERFECT", "GOOD", "OKAY", "POOR"]:
            obs_freq = counts[key] / n_samples
            exp_freq = expected[key]
            # Standard error of binomial distribution
            sigma = math.sqrt(exp_freq * (1.0 - exp_freq) / n_samples)
            three_sigma = 3.0 * sigma
            error = abs(obs_freq - exp_freq)

            assert error <= three_sigma, (
                f"Tier {tier.value} {key} empirical frequency {obs_freq:.4f} deviates from expected {exp_freq:.4f} "
                f"by {error:.4f}, which exceeds 3-sigma tolerance {three_sigma:.4f}"
            )

    @pytest.mark.parametrize("seed", [101, 777, 9999])
    def test_multi_seed_good_tier_stability(self, seed):
        """Verify empirical sampling is stable across multiple independent RNG seeds."""
        n_samples = 10000
        rng = random.Random(seed)
        counts = {"PERFECT": 0, "GOOD": 0, "OKAY": 0, "POOR": 0}
        for _ in range(n_samples):
            rolled = sample_simulation_timing_tier(AbilityTier.GOOD, rng=rng)
            counts[rolled.value] += 1

        expected = self.EXPECTED_BASELINES[AbilityTier.GOOD]
        for key in ["PERFECT", "GOOD", "OKAY", "POOR"]:
            obs_freq = counts[key] / n_samples
            exp_freq = expected[key]
            sigma = math.sqrt(exp_freq * (1.0 - exp_freq) / n_samples)
            assert abs(obs_freq - exp_freq) <= 3.0 * sigma

    def test_roll_simulation_timing_labels_and_split(self):
        """Verify roll_simulation_timing generates appropriate timing labels with ~50/50 early/late split."""
        n_samples = 10000
        rng = random.Random(555)

        label_counts = {
            "PERFECT!": 0,
            "GOOD": 0,
            "EARLY • OKAY": 0,
            "LATE • OKAY": 0,
            "EARLY • POOR": 0,
            "LATE • POOR": 0,
        }

        for _ in range(n_samples):
            tier, label = roll_simulation_timing(AbilityTier.GOOD, rng=rng)
            label_counts[label] += 1
            if tier == TimingTier.PERFECT:
                assert label == "PERFECT!"
            elif tier == TimingTier.GOOD:
                assert label == "GOOD"
            elif tier == TimingTier.OKAY:
                assert label in ("EARLY • OKAY", "LATE • OKAY")
            elif tier == TimingTier.POOR:
                assert label in ("EARLY • POOR", "LATE • POOR")

        # OKAY early vs late split check (~50/50 of OKAY rolls)
        okay_total = label_counts["EARLY • OKAY"] + label_counts["LATE • OKAY"]
        assert okay_total > 1500
        early_okay_ratio = label_counts["EARLY • OKAY"] / okay_total
        assert math.isclose(early_okay_ratio, 0.50, abs_tol=0.05), (
            f"Expected ~0.50 early/late split for OKAY, got {early_okay_ratio}"
        )

        # POOR early vs late split check (~50/50 of POOR rolls)
        poor_total = label_counts["EARLY • POOR"] + label_counts["LATE • POOR"]
        assert poor_total > 300
        early_poor_ratio = label_counts["EARLY • POOR"] / poor_total
        assert math.isclose(early_poor_ratio, 0.50, abs_tol=0.08), (
            f"Expected ~0.50 early/late split for POOR, got {early_poor_ratio}"
        )


# ============================================================================
# 2. Dynamic Modifier Shifts (Fatigue, Leverage, Consistency)
# ============================================================================

class TestDynamicProbabilityShifts:
    """Stress tests dynamic probability modifications under fatigue, leverage, and consistency."""

    @pytest.mark.parametrize("tier", [
        AbilityTier.ELITE,
        AbilityTier.GREAT,
        AbilityTier.GOOD,
        AbilityTier.OKAY,
        AbilityTier.MEDIOCRE,
        AbilityTier.POOR,
    ])
    def test_fatigue_monotonic_degradation(self, tier):
        """Increasing fatigue must strictly increase OKAY+POOR and decrease PERFECT+GOOD."""
        fatigue_levels = [0.0, 25.0, 50.0, 75.0, 100.0]
        bad_timings = []
        good_timings = []

        for fat in fatigue_levels:
            dist = get_simulation_timing_distribution(tier, fatigue_pct=fat)
            bad = dist["OKAY"] + dist["POOR"]
            good = dist["PERFECT"] + dist["GOOD"]
            bad_timings.append(bad)
            good_timings.append(good)

        for i in range(len(fatigue_levels) - 1):
            assert bad_timings[i] < bad_timings[i + 1], (
                f"Tier {tier.value}: OKAY+POOR must strictly increase with fatigue: {bad_timings}"
            )
            assert good_timings[i] > good_timings[i + 1], (
                f"Tier {tier.value}: PERFECT+GOOD must strictly decrease with fatigue: {good_timings}"
            )

    def test_empirical_fatigue_shift_10k_samples(self):
        """Empirical Monte Carlo (N=10,000) verification that fatigue_pct=80% shifts frequency to OKAY/POOR."""
        n_samples = 10000
        rng = random.Random(1234)

        cnt_fresh = {"PERFECT": 0, "GOOD": 0, "OKAY": 0, "POOR": 0}
        cnt_fatigued = {"PERFECT": 0, "GOOD": 0, "OKAY": 0, "POOR": 0}

        for _ in range(n_samples):
            cnt_fresh[sample_simulation_timing_tier(AbilityTier.GOOD, fatigue_pct=0.0, rng=rng).value] += 1
        for _ in range(n_samples):
            cnt_fatigued[sample_simulation_timing_tier(AbilityTier.GOOD, fatigue_pct=80.0, rng=rng).value] += 1

        freq_bad_fresh = (cnt_fresh["OKAY"] + cnt_fresh["POOR"]) / n_samples
        freq_bad_fatigued = (cnt_fatigued["OKAY"] + cnt_fatigued["POOR"]) / n_samples

        assert freq_bad_fatigued > freq_bad_fresh + 0.04, (
            f"80% fatigue should meaningfully increase misses: fresh={freq_bad_fresh}, fatigued={freq_bad_fatigued}"
        )

    def test_leverage_stress_increases_poor_and_okay(self):
        """High leverage with low composure increases POOR/OKAY frequency; high composure mitigates it."""
        dist_neutral = get_simulation_timing_distribution(
            AbilityTier.GOOD,
            composure=80.0,
            is_leverage=False,
        )
        dist_stressed = get_simulation_timing_distribution(
            AbilityTier.GOOD,
            composure=20.0,
            is_leverage=True,
        )
        dist_calm_leverage = get_simulation_timing_distribution(
            AbilityTier.GOOD,
            composure=95.0,
            is_leverage=True,
        )

        bad_neutral = dist_neutral["OKAY"] + dist_neutral["POOR"]
        bad_stressed = dist_stressed["OKAY"] + dist_stressed["POOR"]
        bad_calm_leverage = dist_calm_leverage["OKAY"] + dist_calm_leverage["POOR"]

        assert bad_stressed > bad_neutral, "Stressed pitcher under leverage must have higher misses"
        assert dist_stressed["POOR"] > dist_neutral["POOR"], "Stressed pitcher must have higher POOR probability"
        assert bad_calm_leverage < bad_stressed, "Calm pitcher under leverage must perform better than stressed pitcher"

    def test_consistency_dampening_and_poor_suppression(self):
        """High consistency dampens shift from baseline and steers shifted mass away from POOR towards OKAY."""
        # Test under severe combined stress (leverage + low composure + fatigue)
        high_cons = get_simulation_timing_distribution(
            AbilityTier.GOOD,
            composure=25.0,
            consistency=95.0,
            fatigue_pct=85.0,
            is_leverage=True,
        )
        low_cons = get_simulation_timing_distribution(
            AbilityTier.GOOD,
            composure=25.0,
            consistency=15.0,
            fatigue_pct=85.0,
            is_leverage=True,
        )

        # High consistency preserves more PERFECT + GOOD
        assert (high_cons["PERFECT"] + high_cons["GOOD"]) > (low_cons["PERFECT"] + low_cons["GOOD"])

        # High consistency directs mass away from catastrophic POOR misses
        assert high_cons["POOR"] < low_cons["POOR"]
        assert low_cons["POOR"] > 2.0 * high_cons["POOR"], (
            f"Low consistency pitcher should experience steep spike in POOR: low={low_cons['POOR']}, high={high_cons['POOR']}"
        )

    def test_empirical_consistency_dampening_10k_samples(self):
        """Empirical Monte Carlo (N=10,000) verification of consistency dampening under stress."""
        n_samples = 10000
        rng = random.Random(9876)

        cnt_high = {"PERFECT": 0, "GOOD": 0, "OKAY": 0, "POOR": 0}
        cnt_low = {"PERFECT": 0, "GOOD": 0, "OKAY": 0, "POOR": 0}

        for _ in range(n_samples):
            rolled = sample_simulation_timing_tier(
                AbilityTier.GOOD,
                composure=30.0,
                consistency=90.0,
                fatigue_pct=80.0,
                is_leverage=True,
                rng=rng,
            )
            cnt_high[rolled.value] += 1

        for _ in range(n_samples):
            rolled = sample_simulation_timing_tier(
                AbilityTier.GOOD,
                composure=30.0,
                consistency=20.0,
                fatigue_pct=80.0,
                is_leverage=True,
                rng=rng,
            )
            cnt_low[rolled.value] += 1

        poor_high = cnt_high["POOR"] / n_samples
        poor_low = cnt_low["POOR"] / n_samples

        assert poor_low > poor_high * 2.0, (
            f"Low consistency empirical POOR frequency ({poor_low}) must exceed high consistency ({poor_high}) by > 2x"
        )


# ============================================================================
# 3. Extreme Inputs, Boundary Robustness & Invariance
# ============================================================================

class TestExtremeInputsAndInvariance:
    """Stress tests boundary inputs and probability distribution invariants."""

    @pytest.mark.parametrize(
        "comp,cons,pc,stam,fat_pct,is_lev",
        [
            (-100.0, -50.0, -20, -10.0, -50.0, True),
            (250.0, 300.0, 500, 0.0, 200.0, True),
            (0.0, 0.0, 0, 0.0, 0.0, False),
            (100.0, 100.0, 0, 100.0, 0.0, False),
            (50.0, 50.0, 150, 50.0, None, True),
        ],
    )
    def test_distribution_sum_and_bounds_invariance(self, comp, cons, pc, stam, fat_pct, is_lev):
        """Probabilities must always sum to 1.0000 and remain strictly bounded in [0, 1]."""
        for tier in AbilityTier:
            dist = get_simulation_timing_distribution(
                ability_tier=tier,
                composure=comp,
                consistency=cons,
                pitch_count=pc,
                stamina=stam,
                fatigue_pct=fat_pct,
                is_leverage=is_lev,
            )
            total = sum(dist.values())
            assert math.isclose(total, 1.0000, abs_tol=1e-5), f"Distribution sum was {total}"
            for k, p in dist.items():
                assert 0.0 <= p <= 1.0, f"Probability {k}={p} out of range [0, 1]"

    def test_invalid_tier_string_fallback(self):
        """Invalid tier string safely falls back to GOOD tier without raising exceptions."""
        dist = get_simulation_timing_distribution(ability_tier="NON_EXISTENT_TIER")
        expected_good = BASELINE_TIMING_PROBABILITIES["GOOD"]
        for k in ["PERFECT", "GOOD", "OKAY", "POOR"]:
            assert math.isclose(dist[k], expected_good[k], abs_tol=1e-4)

    def test_timing_dict_case_and_enum_transparency(self):
        """TimingDict returned by get_simulation_timing_distribution transparently handles enum and case lookups."""
        dist = get_simulation_timing_distribution(AbilityTier.ELITE)
        assert dist["perfect"] == dist["PERFECT"] == dist[TimingTier.PERFECT]
        assert dist["good"] == dist["GOOD"] == dist[TimingTier.GOOD]
        assert dist["okay"] == dist["OKAY"] == dist[TimingTier.OKAY]
        assert dist["poor"] == dist["POOR"] == dist[TimingTier.POOR]


# ============================================================================
# 4. End-to-End Simulation Delivery Integration & Telemetry
# ============================================================================

class TestSimulationDeliveryIntegration:
    """Stress tests calculate_pitch_delivery when executing in simulation mode."""

    def test_simulation_delivery_returns_full_telemetry(self):
        """When timing_tier is omitted, calculate_pitch_delivery must roll timing and return full telemetry."""
        rng = random.Random(42)
        res = calculate_pitch_delivery(
            target_x=0.0,
            target_z=2.5,
            command_rating=85.0,
            pitch_count=20,
            stamina=75.0,
            rng=rng,
        )

        assert res["ability_tier"] == "GREAT"
        assert res["timing_tier"] in ("PERFECT", "GOOD", "OKAY", "POOR")
        assert res["timing_label"] in ("PERFECT!", "GOOD", "EARLY • OKAY", "LATE • OKAY", "EARLY • POOR", "LATE • POOR")
        assert res["base_radius_inches"] > 0
        assert res["executed_radius_inches"] > 0
        assert res["radial_miss_inches"] >= 0

        # Radius scaling verification
        mult = TIMING_MULTIPLIERS[getattr(TimingTier, res["timing_tier"])]
        expected_exec_r = round(res["base_radius_inches"] * mult, 3)
        assert math.isclose(res["executed_radius_inches"], expected_exec_r, abs_tol=1e-3)

        # Zero leakage guarantee: miss <= executed radius
        assert res["radial_miss_inches"] <= res["executed_radius_inches"] + 1e-4

    def test_simulation_delivery_zero_leakage_across_1000_pitches(self):
        """Zero leakage invariant (radial_miss <= executed_radius) must hold across 1,000 deliveries."""
        rng = random.Random(999)
        for _ in range(1000):
            res = calculate_pitch_delivery(
                target_x=0.2,
                target_z=2.2,
                command_rating=random.uniform(40.0, 95.0),
                pitch_count=random.randint(0, 110),
                stamina=random.uniform(50.0, 90.0),
                pitcher_hand=random.choice(["R", "L"]),
                rng=rng,
            )
            assert res["radial_miss_inches"] <= res["executed_radius_inches"] + 1e-4, (
                f"Leakage detected: radial_miss={res['radial_miss_inches']}\" > executed_radius={res['executed_radius_inches']}\""
            )
