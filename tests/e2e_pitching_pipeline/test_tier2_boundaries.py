"""
Tier 2: Boundary & Corner Cases Test Suite.
Validates Features F1 through F7 under extreme ratings, edge conditions, and adversarial inputs (Total: 35 tests).
Authoritative Specifications: ORIGINAL_REQUEST.md and PROJECT.md § Interface Contracts.
"""

import math
import random
import pytest

from tests.e2e_pitching_pipeline.conftest import (
    get_tiers_module,
    get_adjusted_ratings_module,
    get_calculations_module,
    evaluate_charging_timing,
    calculate_reticle_geometry,
    calculate_miss_vector,
)
from backend.engine.game_engine.gameday_math import (
    get_max_error_radius_inches,
    calculate_radial_miss_inches,
)


# ============================================================================
# F1 Boundaries: Extreme Ratings & Conditions (5 tests)
# ============================================================================

def test_f1_b1_extreme_command_ratings_below_30_and_above_100():
    """F1.B1: Out-of-bounds ratings (<30, >100) map safely to POOR and ELITE without crashing."""
    tiers = get_tiers_module()
    get_tier = tiers.get_ability_tier
    AbilityTier = tiers.AbilityTier

    # Extreme low ratings
    for low_cmd in [-10.0, 0.0, 15.0, 29.9]:
        assert get_tier(low_cmd) == AbilityTier.POOR, f"Command {low_cmd} must be POOR"

    # Extreme high ratings
    for high_cmd in [100.0, 105.0, 125.0]:
        assert get_tier(high_cmd) == AbilityTier.ELITE, f"Command {high_cmd} must be ELITE"


def test_f1_b2_tier_boundary_infinitesimal_margins():
    """F1.B2: Infinitesimal margins around tier cutoffs resolve to exact tiers."""
    tiers = get_tiers_module()
    get_tier = tiers.get_ability_tier
    AbilityTier = tiers.AbilityTier

    eps = 1e-5
    boundary_pairs = [
        (90.0 - eps, AbilityTier.GREAT, 90.0, AbilityTier.ELITE),
        (80.0 - eps, AbilityTier.GOOD, 80.0, AbilityTier.GREAT),
        (70.0 - eps, AbilityTier.OKAY, 70.0, AbilityTier.GOOD),
        (60.0 - eps, AbilityTier.MEDIOCRE, 60.0, AbilityTier.OKAY),
        (50.0 - eps, AbilityTier.POOR, 50.0, AbilityTier.MEDIOCRE),
    ]

    for below_val, exp_below, at_val, exp_at in boundary_pairs:
        assert get_tier(below_val) == exp_below, f"{below_val} expected {exp_below.value}"
        assert get_tier(at_val) == exp_at, f"{at_val} expected {exp_at.value}"


def test_f1_b3_zero_stamina_vs_max_stamina_fatigue_decay():
    """F1.B3: 0 stamina pitcher experiences maximum fatigue decay, 100 stamina pitcher resists decay."""
    adj = get_adjusted_ratings_module()
    compute_cmd = adj.compute_effective_command

    base_cmd = 80.0

    # 0 stamina at pitch 90
    cmd_zero_stam, tier_zero = compute_cmd(
        base_command=base_cmd,
        pitch_type="4SFB",
        pitch_count=90,
        stamina=0.0,
        composure=75.0,
        consistency=75.0,
    )

    # 100 stamina at pitch 90
    cmd_max_stam, tier_max = compute_cmd(
        base_command=base_cmd,
        pitch_type="4SFB",
        pitch_count=90,
        stamina=100.0,
        composure=75.0,
        consistency=75.0,
    )

    assert cmd_zero_stam < cmd_max_stam
    assert cmd_zero_stam >= 0.0, "Effective command must never be negative"
    assert math.isfinite(cmd_zero_stam) and math.isfinite(cmd_max_stam)


def test_f1_b4_knuckleball_vs_4sfb_cliff_demotion():
    """F1.B4: Knuckleball difficulty modifier (1.35x) causes a tier-cliff drop compared to 4SFB."""
    adj = get_adjusted_ratings_module()
    compute_cmd = adj.compute_effective_command
    tiers = get_tiers_module()

    base_cmd = 72.0  # Borderline GOOD tier

    # 4SFB: 1.00x modifier -> stays in GOOD tier
    cmd_4sfb, tier_4sfb = compute_cmd(
        base_command=base_cmd,
        pitch_type="4SFB",
        pitch_count=20,
        stamina=75.0,
        composure=75.0,
        consistency=75.0,
    )

    # Knuckleball: 1.35x modifier -> drops effective command to ~53.3, falling to MEDIOCRE tier
    cmd_kn, tier_kn = compute_cmd(
        base_command=base_cmd,
        pitch_type="KN",
        pitch_count=20,
        stamina=75.0,
        composure=75.0,
        consistency=75.0,
    )

    assert tier_4sfb == tiers.AbilityTier.GOOD
    assert cmd_kn < cmd_4sfb
    assert tier_kn in (tiers.AbilityTier.OKAY, tiers.AbilityTier.MEDIOCRE, tiers.AbilityTier.POOR)
    assert tier_kn != tiers.AbilityTier.GOOD, "Knuckleball should have dropped pitcher out of GOOD tier"


def test_f1_b5_pitch_count_zero_and_negative_tolerance():
    """F1.B5: Pitch count 0 or negative values are handled safely without mathematical anomalies."""
    adj = get_adjusted_ratings_module()
    compute_cmd = adj.compute_effective_command

    cmd_zero, _ = compute_cmd(
        base_command=75.0,
        pitch_type="4SFB",
        pitch_count=0,
        stamina=75.0,
        composure=75.0,
        consistency=75.0,
    )
    cmd_neg, _ = compute_cmd(
        base_command=75.0,
        pitch_type="4SFB",
        pitch_count=-10,
        stamina=75.0,
        composure=75.0,
        consistency=75.0,
    )

    assert math.isclose(cmd_zero, 75.0, abs_tol=1.0)
    assert math.isclose(cmd_neg, 75.0, abs_tol=1.0)


# ============================================================================
# F2 Boundaries: Radius Scaling Bounds (5 tests)
# ============================================================================

def test_f2_b1_sub_40_command_radius_clamping():
    """F2.B1: Command ratings below 40 clamp base radius to exactly 10.50 inches."""
    for cmd in [39.9, 30.0, 15.0, 0.0, -10.0]:
        r = get_max_error_radius_inches(cmd)
        assert math.isclose(r, 10.50, abs_tol=1e-3), f"Base radius at command {cmd} should clamp to 10.50\", got {r}\""


def test_f2_b2_over_99_command_radius_clamping():
    """F2.B2: Command ratings above 99 clamp base radius to exactly 1.50 inches."""
    for cmd in [99.1, 100.0, 105.0, 150.0]:
        r = get_max_error_radius_inches(cmd)
        assert math.isclose(r, 1.50, abs_tol=1e-3), f"Base radius at command {cmd} should clamp to 1.50\", got {r}\""


def test_f2_b3_perfect_scaling_at_extrema():
    """F2.B3: PERFECT scaling (0.52x) at minimum and maximum anchor radii."""
    tiers = get_tiers_module()
    mult = tiers.TIMING_MULTIPLIERS[tiers.TimingTier.PERFECT]

    # At command 99: base 1.50" -> 0.78"
    r_elite = get_max_error_radius_inches(99.0) * mult
    assert math.isclose(r_elite, 0.78, abs_tol=0.02)

    # At command 40: base 10.50" -> 5.46"
    r_poor = get_max_error_radius_inches(40.0) * mult
    assert math.isclose(r_poor, 5.46, abs_tol=0.05)


def test_f2_b4_poor_scaling_at_extrema():
    """F2.B4: POOR scaling (3.75x) at minimum and maximum anchor radii."""
    tiers = get_tiers_module()
    mult = tiers.TIMING_MULTIPLIERS[tiers.TimingTier.POOR]

    # At command 99: base 1.50" -> 5.625"
    r_elite = get_max_error_radius_inches(99.0) * mult
    assert math.isclose(r_elite, 5.625, abs_tol=0.05)

    # At command 40: base 10.50" -> 39.375"
    r_poor = get_max_error_radius_inches(40.0) * mult
    assert math.isclose(r_poor, 39.375, abs_tol=0.1)


def test_f2_b5_radius_strictly_positive_finite():
    """F2.B5: Executed radius is finite and strictly positive for all valid ratings and timing tiers."""
    tiers = get_tiers_module()
    test_ratings = [0.0, 30.0, 50.0, 70.0, 85.0, 99.0, 105.0]

    for rating in test_ratings:
        base_r = get_max_error_radius_inches(rating)
        for timing in tiers.TimingTier:
            mult = tiers.TIMING_MULTIPLIERS[timing]
            exec_r = base_r * mult
            assert math.isfinite(exec_r) and exec_r > 0.0, f"Invalid executed radius {exec_r} for {rating}, {timing}"


# ============================================================================
# F3 Boundaries: Extreme Probabilities & Distributions (5 tests)
# ============================================================================

def test_f3_b1_probability_sum_invariance_under_extreme_fatigue():
    """F3.B1: Probability distribution continues to sum to 1.0 under 150 pitch count extreme fatigue."""
    calc = get_calculations_module()
    dist = calc.get_simulation_timing_distribution(
        ability_tier="MEDIOCRE",
        composure=40.0,
        consistency=50.0,
        pitch_count=150,
        stamina=40.0,
        is_leverage=True,
    )

    total = sum(dist.values())
    assert math.isclose(total, 1.00, abs_tol=1e-5), f"Distribution sum {total} != 1.0 under extreme fatigue"


def test_f3_b2_zero_composure_maximum_stress_saturation():
    """F3.B2: Composure rating 0 under high leverage keeps all probabilities in [0.0, 1.0]."""
    calc = get_calculations_module()
    dist = calc.get_simulation_timing_distribution(
        ability_tier="POOR",
        composure=0.0,
        consistency=0.0,
        pitch_count=100,
        stamina=50.0,
        is_leverage=True,
    )

    for tier, prob in dist.items():
        assert 0.0 <= prob <= 1.0, f"Probability for {tier} ({prob}) out of bounds [0, 1]"
    assert math.isclose(sum(dist.values()), 1.00, abs_tol=1e-5)


def test_f3_b3_maximum_consistency_100_variance_suppression():
    """F3.B3: Consistency 100 preserves baseline distribution against degradation under stress."""
    calc = get_calculations_module()

    # Under stress, consistency 100 vs consistency 0
    dist_100 = calc.get_simulation_timing_distribution(
        ability_tier="GOOD",
        composure=30.0,
        consistency=100.0,
        pitch_count=80,
        stamina=65.0,
        is_leverage=True,
    )
    dist_0 = calc.get_simulation_timing_distribution(
        ability_tier="GOOD",
        composure=30.0,
        consistency=0.0,
        pitch_count=80,
        stamina=65.0,
        is_leverage=True,
    )

    # Poor probability should be much lower with max consistency
    assert dist_100["POOR"] < dist_0["POOR"]


def test_f3_b4_all_six_ability_tiers_valid_distribution():
    """F3.B4: get_simulation_timing_distribution produces valid probabilities for all 6 tiers."""
    calc = get_calculations_module()
    all_tiers = ["ELITE", "GREAT", "GOOD", "OKAY", "MEDIOCRE", "POOR"]

    for tier in all_tiers:
        dist = calc.get_simulation_timing_distribution(
            ability_tier=tier,
            composure=75.0,
            consistency=75.0,
            pitch_count=30,
            stamina=75.0,
        )
        assert len(dist) == 4, f"Distribution for {tier} missing timing tiers"
        assert math.isclose(sum(dist.values()), 1.00, abs_tol=1e-5)
        for k, v in dist.items():
            assert v >= 0.0


def test_f3_b5_extreme_rng_seeds_determinism():
    """F3.B5: Simulation timing roll is 100% deterministic given identical RNG seeds."""
    calc = get_calculations_module()
    sample_roll = calc.sample_simulation_timing_tier

    rng1 = random.Random(99999)
    rng2 = random.Random(99999)

    rolls_1 = [sample_roll(ability_tier="GOOD", rng=rng1) for _ in range(50)]
    rolls_2 = [sample_roll(ability_tier="GOOD", rng=rng2) for _ in range(50)]

    assert rolls_1 == rolls_2, "Rolls with identical seeds must be identical"


# ============================================================================
# F4 Boundaries: Dispersion Spatial Boundaries (5 tests)
# ============================================================================

def test_f4_b1_target_at_extreme_viewport_corners():
    """F4.B1: Targeting at extreme viewport corners generates valid finite coordinates."""
    calc = get_calculations_module()
    tiers = get_tiers_module()

    corners = [
        (-2.0, 0.0),
        (2.0, 0.0),
        (-2.0, 4.5),
        (2.0, 4.5),
    ]

    for tx, tz in corners:
        delivery = calc.calculate_pitch_delivery(
            target_x=tx,
            target_z=tz,
            command_rating=70.0,
            pitch_count=10,
            timing_tier=tiers.TimingTier.GOOD,
            timing_label="GOOD",
        )
        assert math.isfinite(delivery["realized_x"])
        assert math.isfinite(delivery["realized_z"])
        assert math.isfinite(delivery["radial_miss_inches"])


def test_f4_b2_extreme_early_release_direction_sector():
    """F4.B2: 100% early release for RHP is bounded strictly within the upper arm-side quadrant."""
    calc = get_calculations_module()
    tiers = get_tiers_module()

    rng = random.Random(777)
    target_x, target_z = 0.0, 2.50

    for _ in range(30):
        delivery = calc.calculate_pitch_delivery(
            target_x=target_x,
            target_z=target_z,
            command_rating=50.0,
            pitch_count=50,
            timing_tier=tiers.TimingTier.POOR,
            timing_label="EARLY • POOR",
            pitcher_hand="R",
            rng=rng,
        )
        dx = delivery["realized_x"] - target_x
        dz = delivery["realized_z"] - target_z
        # Must be in upper arm-side half (dz > 0, dx < 0)
        assert dz >= -0.05, f"Early release spiked low: dz={dz}"
        assert dx <= 0.05, f"Early RHP release missed arm side: dx={dx}"


def test_f4_b3_extreme_late_release_dirt_spike():
    """F4.B3: Extreme late release is bounded strictly in the downward dirt sector."""
    calc = get_calculations_module()
    tiers = get_tiers_module()

    rng = random.Random(888)
    target_x, target_z = 0.0, 1.80  # Low target

    for _ in range(30):
        delivery = calc.calculate_pitch_delivery(
            target_x=target_x,
            target_z=target_z,
            command_rating=50.0,
            pitch_count=50,
            timing_tier=tiers.TimingTier.POOR,
            timing_label="LATE • POOR",
            rng=rng,
        )
        dz = delivery["realized_z"] - target_z
        assert dz <= 0.05, f"Late release missed high: dz={dz}"


def test_f4_b4_zero_sigma_or_zero_radius_convergence():
    """F4.B4: Zero error radius forces pitch delivery to converge exactly onto the target."""
    calc = get_calculations_module()

    target_x, target_z = 0.45, 2.80
    delivery = calc.calculate_pitch_delivery(
        target_x=target_x,
        target_z=target_z,
        command_rating=99.0,
        pitch_count=0,
        precomputed_sigma=0.0,
        precomputed_max_radius_in=0.0,
    )

    assert math.isclose(delivery["realized_x"], target_x, abs_tol=1e-5)
    assert math.isclose(delivery["realized_z"], target_z, abs_tol=1e-5)
    assert math.isclose(delivery["radial_miss_inches"], 0.0, abs_tol=1e-5)


def test_f4_b5_closed_form_truncated_circle_guarantee():
    """F4.B5: Sampling 500 pitches never escapes the hard maximum error circle (zero leakage)."""
    calc = get_calculations_module()
    tiers = get_tiers_module()

    rng = random.Random(999)
    target_x, target_z = -0.30, 2.10

    for _ in range(500):
        delivery = calc.calculate_pitch_delivery(
            target_x=target_x,
            target_z=target_z,
            command_rating=60.0,
            pitch_count=35,
            timing_tier=tiers.TimingTier.OKAY,
            timing_label="OKAY",
            rng=rng,
        )
        radial_miss = delivery["radial_miss_inches"]
        max_r = delivery["executed_radius_inches"]
        assert radial_miss <= max_r + 1e-4, f"Radial miss {radial_miss}\" leaked past max radius {max_r}\""


# ============================================================================
# F5 Boundaries: API Corner Cases & Error Handling (5 tests)
# ============================================================================

def test_f5_b1_empty_payload_safe_handling(client):
    """F5.B1: POST /api/pitch/throw with empty JSON body does not trigger 500 Internal Error."""
    response = client.post("/api/pitch/throw", json={})
    # Must be 200 (AI fallback) or 400 (validation), never 500
    assert response.status_code in (200, 400), f"Unexpected status {response.status_code}: {response.data}"


def test_f5_b2_non_numeric_coordinates_validation(client):
    """F5.B2: Non-numeric target coordinates return HTTP 400 Bad Request."""
    payload = {
        "selection_mode": "user",
        "pitch_name": "4-Seam Fastball",
        "target_x": "not_a_number",
        "target_z": 2.50,
    }
    response = client.post("/api/pitch/throw", json=payload)
    assert response.status_code == 400


def test_f5_b3_case_insensitive_timing_tier_normalization(client):
    """F5.B3: timing_tier accepts lowercase 'perfect' and normalizes correctly."""
    payload = {
        "selection_mode": "user",
        "pitch_name": "4-Seam Fastball",
        "pitch_intent": "STRIKE",
        "target_zone": "heart",
        "target_x": 0.0,
        "target_z": 2.50,
        "timing_tier": "perfect",
        "timing_label": "perfect!",
    }
    response = client.post("/api/pitch/throw", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["execution"]["timing_tier"] == "PERFECT"


def test_f5_b4_pitch_in_flight_concurrency_conflict(client):
    """F5.B4: Attempting to throw a pitch while previous pitch is in flight returns 409 Conflict."""
    payload = {
        "selection_mode": "user",
        "pitch_name": "4-Seam Fastball",
        "target_zone": "heart",
        "target_x": 0.0,
        "target_z": 2.50,
    }
    # First pitch thrown
    res1 = client.post("/api/pitch/throw", json=payload)
    assert res1.status_code == 200

    # Second pitch thrown immediately without resolve
    res2 = client.post("/api/pitch/throw", json=payload)
    assert res2.status_code == 409, f"Expected 409 Conflict, got {res2.status_code}"


def test_f5_b5_extreme_large_coordinate_values(client):
    """F5.B5: Outrageously huge coordinates (e.g. x=9999.0) are rejected with 400."""
    payload = {
        "selection_mode": "user",
        "pitch_name": "4-Seam Fastball",
        "target_x": 9999.0,
        "target_z": 9999.0,
    }
    response = client.post("/api/pitch/throw", json=payload)
    assert response.status_code in (400, 422), f"Expected 400/422 for extreme coords, got {response.status_code}"


# ============================================================================
# F6 Boundaries: Interactive Delivery Edge Cases (5 tests)
# ============================================================================

def test_f6_b1_zero_and_sub_millisecond_tap():
    """F6.B1: Instantaneous button taps (0ms to 5ms) lock in EARLY • POOR."""
    for ms in [0.0, 1.0, 5.0]:
        tier, label = evaluate_charging_timing(ms, target_sweet_spot_ms=1000.0)
        assert tier == "POOR"
        assert label == "EARLY • POOR"


def test_f6_b2_excessive_hold_duration_timeout():
    """F6.B2: Holding button indefinitely (e.g. 5000ms) locks in LATE • POOR."""
    for ms in [2000.0, 5000.0, 10000.0]:
        tier, label = evaluate_charging_timing(ms, target_sweet_spot_ms=1000.0)
        assert tier == "POOR"
        assert label == "LATE • POOR"


def test_f6_b3_exact_sweet_spot_boundary_thresholds():
    """F6.B3: Boundary thresholds between GOOD and PERFECT transition with millisecond precision."""
    target = 1000.0

    # 949ms -> GOOD (Early), 950ms -> PERFECT
    tier_below, _ = evaluate_charging_timing(949.0, target)
    tier_at, _ = evaluate_charging_timing(950.0, target)
    assert tier_below == "GOOD"
    assert tier_at == "PERFECT"

    # 1050ms -> PERFECT, 1051ms -> GOOD (Late)
    tier_top, _ = evaluate_charging_timing(1050.0, target)
    tier_above, _ = evaluate_charging_timing(1051.0, target)
    assert tier_top == "PERFECT"
    assert tier_above == "GOOD"


def test_f6_b4_negative_hold_duration_handling():
    """F6.B4: Defensive guard against negative hold duration defaults safely to POOR."""
    tier, label = evaluate_charging_timing(-100.0, 1000.0)
    assert tier == "POOR"
    assert "POOR" in label


def test_f6_b5_label_consistency_for_all_possible_timings():
    """F6.B5: Full spectrum sampling from 0ms to 2000ms generates valid tier and label without exceptions."""
    valid_tiers = {"PERFECT", "GOOD", "OKAY", "POOR"}

    for ms in range(0, 2000, 25):
        tier, label = evaluate_charging_timing(float(ms), 1000.0)
        assert tier in valid_tiers
        assert isinstance(label, str) and len(label) > 0


# ============================================================================
# F7 Boundaries: Reticle & Miss Vector Boundaries (5 tests)
# ============================================================================

def test_f7_b1_reticle_scale_at_command_zero():
    """F7.B1: Base reticle at command 0 is 10.50\", POOR reticle expands to 39.375\"."""
    base_r = get_max_error_radius_inches(0.0)
    assert math.isclose(base_r, 10.50, abs_tol=1e-3)

    geom = calculate_reticle_geometry(base_r, "POOR")
    assert math.isclose(geom["executed_radius_inches"], 39.375, abs_tol=0.1)


def test_f7_b2_reticle_scale_at_command_100():
    """F7.B2: Base reticle at command 100 is 1.50\", PERFECT reticle contracts to 0.78\"."""
    base_r = get_max_error_radius_inches(100.0)
    assert math.isclose(base_r, 1.50, abs_tol=1e-3)

    geom = calculate_reticle_geometry(base_r, "PERFECT")
    assert math.isclose(geom["executed_radius_inches"], 0.78, abs_tol=0.02)


def test_f7_b3_exact_zero_miss_vector():
    """F7.B3: Perfect landing on target yields exactly 0.00\" miss vector."""
    vec = calculate_miss_vector(0.0, 2.50, 0.0, 2.50)
    assert vec["delta_x_in"] == 0.0
    assert vec["delta_z_in"] == 0.0
    assert vec["radial_miss_inches"] == 0.0


def test_f7_b4_miss_vector_scaling_ft_to_inches():
    """F7.B4: Statcast feet to inches coordinate conversion is exactly 12.0 inches/foot."""
    # 0.25 ft = 3.0 in, 0.50 ft = 6.0 in
    vec = calculate_miss_vector(0.0, 2.0, 0.25, 2.50)
    assert math.isclose(vec["delta_x_in"], 3.00, abs_tol=1e-2)
    assert math.isclose(vec["delta_z_in"], 6.00, abs_tol=1e-2)
    # Hypotenuse: sqrt(3^2 + 6^2) = sqrt(45) ~ 6.708"
    assert math.isclose(vec["radial_miss_inches"], 6.71, abs_tol=0.05)


def test_f7_b5_reticle_bloom_ratio_invariance_with_base_size():
    """F7.B5: Bloom ratio is strictly invariant to base circle size across all tiers."""
    for base in [1.0, 2.5, 5.0, 7.0]:
        g_perf = calculate_reticle_geometry(base, "PERFECT")
        g_good = calculate_reticle_geometry(base, "GOOD")
        g_okay = calculate_reticle_geometry(base, "OKAY")
        g_poor = calculate_reticle_geometry(base, "POOR")

        assert math.isclose(g_perf["bloom_ratio"], 0.52, rel_tol=0.05)
        assert math.isclose(g_good["bloom_ratio"], 1.00, rel_tol=0.01)
        assert math.isclose(g_okay["bloom_ratio"], 1.97, rel_tol=0.05)
        assert math.isclose(g_poor["bloom_ratio"], 3.75, rel_tol=0.05)
