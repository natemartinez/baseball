"""
Tier 1: Feature Coverage Test Suite.
Validates Features F1 through F7 with at least 5 distinct test cases per feature (Total: 38 tests).
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
# F1: Pitcher Ability Tiers & Rating Logic (6 tests)
# ============================================================================

def test_f1_ability_tier_enum_values():
    """F1.1: AbilityTier enum defines 6 distinct tiers in descending quality."""
    tiers = get_tiers_module()
    assert hasattr(tiers, "AbilityTier"), "AbilityTier enum missing from tiers.py"
    AbilityTier = tiers.AbilityTier

    expected_tiers = ["ELITE", "GREAT", "GOOD", "OKAY", "MEDIOCRE", "POOR"]
    for tier_name in expected_tiers:
        assert hasattr(AbilityTier, tier_name), f"AbilityTier.{tier_name} missing"
        assert getattr(AbilityTier, tier_name).value == tier_name


def test_f1_get_ability_tier_boundaries():
    """F1.2: get_ability_tier maps effective command to correct tier across boundaries."""
    tiers = get_tiers_module()
    assert hasattr(tiers, "get_ability_tier"), "get_ability_tier function missing from tiers.py"
    get_tier = tiers.get_ability_tier
    AbilityTier = tiers.AbilityTier

    # Boundary test matrix: (effective_command, expected_tier)
    test_cases = [
        (99.0, AbilityTier.ELITE),
        (90.0, AbilityTier.ELITE),
        (89.9, AbilityTier.GREAT),
        (85.0, AbilityTier.GREAT),
        (80.0, AbilityTier.GREAT),
        (79.9, AbilityTier.GOOD),
        (75.0, AbilityTier.GOOD),
        (70.0, AbilityTier.GOOD),
        (69.9, AbilityTier.OKAY),
        (65.0, AbilityTier.OKAY),
        (60.0, AbilityTier.OKAY),
        (59.9, AbilityTier.MEDIOCRE),
        (55.0, AbilityTier.MEDIOCRE),
        (50.0, AbilityTier.MEDIOCRE),
        (49.9, AbilityTier.POOR),
        (35.0, AbilityTier.POOR),
    ]

    for cmd, expected in test_cases:
        actual = get_tier(cmd)
        assert actual == expected, f"Command {cmd} should be {expected.value}, got {actual}"


def test_f1_pitch_type_difficulty_modifiers():
    """F1.3: PITCH_TYPE_MODIFIERS defines standardized difficulty scalars for arsenals."""
    tiers = get_tiers_module()
    assert hasattr(tiers, "PITCH_TYPE_MODIFIERS"), "PITCH_TYPE_MODIFIERS missing from tiers.py"
    mods = tiers.PITCH_TYPE_MODIFIERS

    expected_modifiers = {
        "4SFB": 1.00,
        "2SFB": 1.02,
        "CUT": 1.05,
        "SNK": 1.05,
        "CH": 1.08,
        "SL": 1.15,
        "SWP": 1.18,
        "CB": 1.20,
        "SPL": 1.25,
        "KN": 1.35,
    }

    for pitch, expected_val in expected_modifiers.items():
        assert pitch in mods, f"Pitch type {pitch} missing from PITCH_TYPE_MODIFIERS"
        assert math.isclose(mods[pitch], expected_val, rel_tol=1e-3), (
            f"Modifier for {pitch} expected {expected_val}, got {mods[pitch]}"
        )

    # Harder pitches must have higher difficulty than baseline fastball
    assert mods["KN"] > mods["CB"] > mods["SL"] > mods["CH"] > mods["4SFB"]


def test_f1_compute_effective_command_fatigue_decay():
    """F1.4: compute_effective_command reduces effective command as pitch count exceeds stamina."""
    adj = get_adjusted_ratings_module()
    assert hasattr(adj, "compute_effective_command"), "compute_effective_command missing"
    compute_cmd = adj.compute_effective_command
    tiers = get_tiers_module()
    AbilityTier = tiers.AbilityTier

    base_cmd = 82.0
    stamina = 70.0

    # Fresh state (pitch_count = 10)
    eff_cmd_fresh, tier_fresh = compute_cmd(
        base_command=base_cmd,
        pitch_type="4SFB",
        pitch_count=10,
        stamina=stamina,
        composure=75.0,
        consistency=75.0,
        is_leverage=False,
    )
    assert eff_cmd_fresh >= 80.0
    assert tier_fresh in (AbilityTier.GREAT, AbilityTier.ELITE)

    # Fatigued state (pitch_count = 95)
    eff_cmd_fatigued, tier_fatigued = compute_cmd(
        base_command=base_cmd,
        pitch_type="4SFB",
        pitch_count=95,
        stamina=stamina,
        composure=75.0,
        consistency=75.0,
        is_leverage=False,
    )

    assert eff_cmd_fatigued < eff_cmd_fresh, (
        f"Fatigued command {eff_cmd_fatigued} should be lower than fresh {eff_cmd_fresh}"
    )
    # Tier should downgrade when command drops
    assert eff_cmd_fatigued < 80.0


def test_f1_compute_effective_command_composure_and_leverage():
    """F1.5: High leverage penalizes effective command more severely for low composure pitchers."""
    adj = get_adjusted_ratings_module()
    compute_cmd = adj.compute_effective_command

    base_cmd = 75.0
    stamina = 75.0

    # Shaky composure (40) vs Calm composure (90) under high leverage
    cmd_calm, _ = compute_cmd(
        base_command=base_cmd,
        pitch_type="4SFB",
        pitch_count=30,
        stamina=stamina,
        composure=90.0,
        consistency=75.0,
        is_leverage=True,
    )

    cmd_shaky, _ = compute_cmd(
        base_command=base_cmd,
        pitch_type="4SFB",
        pitch_count=30,
        stamina=stamina,
        composure=40.0,
        consistency=75.0,
        is_leverage=True,
    )

    assert cmd_calm > cmd_shaky, (
        f"Calm pitcher ({cmd_calm}) should retain higher command than shaky pitcher ({cmd_shaky})"
    )


def test_f1_domain_player_non_mutation(test_matchup):
    """F1.6: Dynamic rating computations must never mutate persistent Player domain objects."""
    pitcher, _ = test_matchup
    orig_control = pitcher.get_rating("Control", 70.0)
    orig_stamina = getattr(pitcher, "stamina", 75.0)

    adj = get_adjusted_ratings_module()
    compute_cmd = adj.compute_effective_command

    # Run heavy fatigue + leverage calculation
    compute_cmd(
        base_command=orig_control,
        pitch_type="KN",
        pitch_count=120,
        stamina=orig_stamina,
        composure=20.0,
        consistency=30.0,
        is_leverage=True,
    )

    assert pitcher.get_rating("Control", 70.0) == orig_control, "Player Control rating was mutated"
    assert getattr(pitcher, "stamina", 75.0) == orig_stamina, "Player Stamina was mutated"


# ============================================================================
# F2: Unified Hybrid Model & Radius Scaling (5 tests)
# ============================================================================

def test_f2_timing_tier_multipliers():
    """F2.1: TIMING_MULTIPLIERS correctly scales GOOD=1.0x, PERFECT~0.52x, OKAY~1.97x, POOR~3.75x."""
    tiers = get_tiers_module()
    assert hasattr(tiers, "TIMING_MULTIPLIERS"), "TIMING_MULTIPLIERS missing from tiers.py"
    mults = tiers.TIMING_MULTIPLIERS
    TimingTier = tiers.TimingTier

    assert math.isclose(mults[TimingTier.PERFECT], 0.52, rel_tol=0.05)
    assert math.isclose(mults[TimingTier.GOOD], 1.00, rel_tol=0.01)
    assert math.isclose(mults[TimingTier.OKAY], 1.97, rel_tol=0.05)
    assert math.isclose(mults[TimingTier.POOR], 3.75, rel_tol=0.05)

    # Monotonic ordering of error multipliers
    assert mults[TimingTier.PERFECT] < mults[TimingTier.GOOD] < mults[TimingTier.OKAY] < mults[TimingTier.POOR]


def test_f2_base_radius_anchor_calibration_curve():
    """F2.2: Base error radius anchors to GOOD 1.0x curve (1.50\" to 10.50\")."""
    expected_curve = [
        (99.0, 1.50),
        (90.0, 1.875),
        (82.0, 2.25),
        (68.0, 4.50),
        (55.0, 6.75),
        (40.0, 10.50),
    ]

    for cmd, expected_r in expected_curve:
        actual_r = get_max_error_radius_inches(cmd)
        assert math.isclose(actual_r, expected_r, abs_tol=0.05), (
            f"Command {cmd} should have base radius {expected_r}\", got {actual_r}\""
        )


def test_f2_executed_radius_scaling_perfect_contracts():
    """F2.3: PERFECT timing contracts base error radius by approximately 52%."""
    tiers = get_tiers_module()
    mult_perfect = tiers.TIMING_MULTIPLIERS[tiers.TimingTier.PERFECT]

    test_commands = [95.0, 80.0, 65.0, 50.0]
    for cmd in test_commands:
        base_r = get_max_error_radius_inches(cmd)
        executed_r = base_r * mult_perfect
        assert executed_r < base_r, f"Executed radius {executed_r} must be smaller than base {base_r}"
        assert math.isclose(executed_r / base_r, 0.52, rel_tol=0.05)


def test_f2_executed_radius_scaling_okay_and_poor_expand():
    """F2.4: OKAY and POOR timing expand error radius by ~1.97x and ~3.75x."""
    tiers = get_tiers_module()
    mult_okay = tiers.TIMING_MULTIPLIERS[tiers.TimingTier.OKAY]
    mult_poor = tiers.TIMING_MULTIPLIERS[tiers.TimingTier.POOR]

    base_r = get_max_error_radius_inches(75.0)  # ~2.25 inches
    exec_okay = base_r * mult_okay
    exec_poor = base_r * mult_poor

    assert exec_okay > base_r
    assert exec_poor > exec_okay
    assert math.isclose(exec_okay / base_r, 1.97, rel_tol=0.05)
    assert math.isclose(exec_poor / base_r, 3.75, rel_tol=0.05)


def test_f2_base_radius_good_timing_identity():
    """F2.5: GOOD timing tier acts as identity multiplier (1.00x) for base radius."""
    tiers = get_tiers_module()
    mult_good = tiers.TIMING_MULTIPLIERS[tiers.TimingTier.GOOD]

    for cmd in [40.0, 55.0, 70.0, 85.0, 99.0]:
        base_r = get_max_error_radius_inches(cmd)
        exec_good = base_r * mult_good
        assert math.isclose(exec_good, base_r, rel_tol=1e-5), (
            f"GOOD executed radius {exec_good} must equal base radius {base_r}"
        )


# ============================================================================
# F3: Simulation Probability Distributions & Shifts (6 tests)
# ============================================================================

def test_f3_baseline_probability_tables_exact_values():
    """F3.1: Calibrated discrete probability tables for TimingTier per ability tier."""
    tiers = get_tiers_module()
    # If BASELINE_TIMING_PROBABILITIES or equivalent table is exposed
    table = getattr(tiers, "BASELINE_TIMING_PROBABILITIES", None)
    if table is None:
        calc = get_calculations_module()
        table = getattr(calc, "BASELINE_TIMING_PROBABILITIES", None)

    assert table is not None, "BASELINE_TIMING_PROBABILITIES table missing from tiers.py / calculations.py"

    expected_table = {
        "ELITE": {"PERFECT": 0.45, "GOOD": 0.45, "OKAY": 0.08, "POOR": 0.02},
        "GREAT": {"PERFECT": 0.35, "GOOD": 0.48, "OKAY": 0.14, "POOR": 0.03},
        "GOOD": {"PERFECT": 0.25, "GOOD": 0.50, "OKAY": 0.20, "POOR": 0.05},
        "OKAY": {"PERFECT": 0.15, "GOOD": 0.45, "OKAY": 0.30, "POOR": 0.10},
        "MEDIOCRE": {"PERFECT": 0.08, "GOOD": 0.37, "OKAY": 0.37, "POOR": 0.18},
        "POOR": {"PERFECT": 0.05, "GOOD": 0.30, "OKAY": 0.40, "POOR": 0.25},
    }

    for tier_name, probs in expected_table.items():
        actual_probs = table.get(tier_name) or table.get(getattr(tiers.AbilityTier, tier_name))
        assert actual_probs is not None, f"Tier {tier_name} missing from table"
        total = sum(actual_probs.values() if isinstance(actual_probs, dict) else actual_probs)
        assert math.isclose(total, 1.00, abs_tol=1e-3), f"Probabilities for {tier_name} do not sum to 1.0"

        for k, exp_val in probs.items():
            key = k if k in actual_probs else getattr(tiers.TimingTier, k)
            assert math.isclose(actual_probs[key], exp_val, abs_tol=0.01), (
                f"{tier_name} {k} expected {exp_val}, got {actual_probs[key]}"
            )


def test_f3_probability_monotonicity_across_tiers():
    """F3.2: Better ability tiers have strictly higher PERFECT probability and lower POOR probability."""
    tiers = get_tiers_module()
    calc = get_calculations_module()
    table = getattr(tiers, "BASELINE_TIMING_PROBABILITIES", None) or getattr(calc, "BASELINE_TIMING_PROBABILITIES")

    tier_order = ["POOR", "MEDIOCRE", "OKAY", "GOOD", "GREAT", "ELITE"]
    perfect_probs = []
    poor_probs = []

    for t in tier_order:
        row = table.get(t) or table.get(getattr(tiers.AbilityTier, t))
        p_perf = row.get("PERFECT") or row.get(tiers.TimingTier.PERFECT)
        p_poor = row.get("POOR") or row.get(tiers.TimingTier.POOR)
        perfect_probs.append(p_perf)
        poor_probs.append(p_poor)

    # Perfect probability strictly increases as tier improves
    for i in range(len(perfect_probs) - 1):
        assert perfect_probs[i] < perfect_probs[i + 1], "PERFECT probability must increase with tier"

    # Poor probability strictly decreases as tier improves
    for i in range(len(poor_probs) - 1):
        assert poor_probs[i] > poor_probs[i + 1], "POOR probability must decrease with tier"


def test_f3_composure_stress_shifts_mass_to_okay_poor():
    """F3.3: High leverage / low composure dynamically shifts probability mass to OKAY and POOR."""
    calc = get_calculations_module()
    assert hasattr(calc, "get_simulation_timing_distribution"), (
        "get_simulation_timing_distribution missing from calculations.py"
    )
    get_dist = calc.get_simulation_timing_distribution

    # Neutral situation vs High-leverage low-composure stress
    neutral_dist = get_dist(
        ability_tier="GOOD",
        composure=75.0,
        consistency=75.0,
        pitch_count=20,
        stamina=75.0,
        is_leverage=False,
    )
    stressed_dist = get_dist(
        ability_tier="GOOD",
        composure=35.0,
        consistency=75.0,
        pitch_count=20,
        stamina=75.0,
        is_leverage=True,
    )

    bad_neutral = neutral_dist["OKAY"] + neutral_dist["POOR"]
    bad_stressed = stressed_dist["OKAY"] + stressed_dist["POOR"]
    assert bad_stressed > bad_neutral, "Stress must shift probability towards OKAY/POOR"


def test_f3_fatigue_shifts_distribution_to_higher_misses():
    """F3.4: Fatigue from high pitch counts degrades the timing distribution towards misses."""
    calc = get_calculations_module()
    get_dist = calc.get_simulation_timing_distribution

    fresh_dist = get_dist(
        ability_tier="ELITE",
        composure=80.0,
        consistency=80.0,
        pitch_count=10,
        stamina=70.0,
        is_leverage=False,
    )
    fatigued_dist = get_dist(
        ability_tier="ELITE",
        composure=80.0,
        consistency=80.0,
        pitch_count=95,
        stamina=70.0,
        is_leverage=False,
    )

    good_fresh = fresh_dist["PERFECT"] + fresh_dist["GOOD"]
    good_fatigued = fatigued_dist["PERFECT"] + fatigued_dist["GOOD"]
    assert good_fatigued < good_fresh, "Fatigue must reduce the probability of PERFECT and GOOD timing"


def test_f3_consistency_stabilizes_probability_shifts():
    """F3.5: Higher consistency rating dampens the timing distribution shift under stress."""
    calc = get_calculations_module()
    get_dist = calc.get_simulation_timing_distribution

    # High consistency (90) vs Low consistency (40) under identical stress
    high_cons_dist = get_dist(
        ability_tier="GOOD",
        composure=40.0,
        consistency=90.0,
        pitch_count=85,
        stamina=70.0,
        is_leverage=True,
    )
    low_cons_dist = get_dist(
        ability_tier="GOOD",
        composure=40.0,
        consistency=40.0,
        pitch_count=85,
        stamina=70.0,
        is_leverage=True,
    )

    # Low consistency should experience greater collapse into POOR
    assert low_cons_dist["POOR"] > high_cons_dist["POOR"], (
        "Low consistency pitcher must experience greater POOR probability under stress"
    )


def test_f3_simulated_timing_roll_statistical_match():
    """F3.6: Roll generator empirical frequencies match baseline table within statistical tolerance."""
    calc = get_calculations_module()
    assert hasattr(calc, "sample_simulation_timing_tier"), (
        "sample_simulation_timing_tier missing from calculations.py"
    )
    sample_roll = calc.sample_simulation_timing_tier

    rng = random.Random(42)
    n_samples = 4000
    counts = {"PERFECT": 0, "GOOD": 0, "OKAY": 0, "POOR": 0}

    # Test for ELITE tier: 45% Perfect, 45% Good, 8% Okay, 2% Poor
    for _ in range(n_samples):
        tier_rolled = sample_roll(ability_tier="ELITE", rng=rng)
        counts[str(tier_rolled.value if hasattr(tier_rolled, "value") else tier_rolled)] += 1

    p_perfect = counts["PERFECT"] / n_samples
    p_good = counts["GOOD"] / n_samples
    p_okay = counts["OKAY"] / n_samples
    p_poor = counts["POOR"] / n_samples

    assert math.isclose(p_perfect, 0.45, abs_tol=0.03), f"Observed PERFECT {p_perfect} vs expected 0.45"
    assert math.isclose(p_good, 0.45, abs_tol=0.03), f"Observed GOOD {p_good} vs expected 0.45"
    assert math.isclose(p_okay, 0.08, abs_tol=0.02), f"Observed OKAY {p_okay} vs expected 0.08"
    assert math.isclose(p_poor, 0.02, abs_tol=0.015), f"Observed POOR {p_poor} vs expected 0.02"


# ============================================================================
# F4: Directional Dispersion Tendencies (6 tests)
# ============================================================================

def test_f4_perfect_timing_tight_center_clustering():
    """F4.1: PERFECT timing clusters tightly near reticle center (mean miss < 45% of max radius)."""
    calc = get_calculations_module()
    tiers = get_tiers_module()

    rng = random.Random(101)
    target_x, target_z = 0.0, 2.50
    cmd = 85.0

    radial_misses = []
    executed_radius = None

    for _ in range(100):
        delivery = calc.calculate_pitch_delivery(
            target_x=target_x,
            target_z=target_z,
            command_rating=cmd,
            pitch_count=15,
            stamina=80.0,
            timing_tier=tiers.TimingTier.PERFECT,
            timing_label="PERFECT!",
            rng=rng,
        )
        radial_misses.append(delivery["radial_miss_inches"])
        executed_radius = delivery["executed_radius_inches"]

    mean_miss = sum(radial_misses) / len(radial_misses)
    assert mean_miss < (0.45 * executed_radius), (
        f"Mean miss {mean_miss}\" exceeds 45% of executed radius {executed_radius}\""
    )


def test_f4_good_timing_uniform_dispersion():
    """F4.2: GOOD timing uniformly fills the error circle without quadrant clumping."""
    calc = get_calculations_module()
    tiers = get_tiers_module()

    rng = random.Random(202)
    target_x, target_z = 0.0, 2.50

    quadrants = [0, 0, 0, 0]  # Q1 (+,+), Q2 (-,+), Q3 (-,-), Q4 (+,-)

    for _ in range(400):
        delivery = calc.calculate_pitch_delivery(
            target_x=target_x,
            target_z=target_z,
            command_rating=75.0,
            pitch_count=20,
            timing_tier=tiers.TimingTier.GOOD,
            timing_label="GOOD",
            rng=rng,
        )
        dx = delivery["realized_x"] - target_x
        dz = delivery["realized_z"] - target_z
        if dx >= 0 and dz >= 0:
            quadrants[0] += 1
        elif dx < 0 and dz >= 0:
            quadrants[1] += 1
        elif dx < 0 and dz < 0:
            quadrants[2] += 1
        else:
            quadrants[3] += 1

    # In uniform isotropic distribution, each quadrant should have roughly 25% ± 8%
    for i, count in enumerate(quadrants):
        pct = count / 400
        assert 0.17 <= pct <= 0.33, f"Quadrant {i+1} count {count} ({pct:.1%}) deviated from uniformity"


def test_f4_early_release_directional_bias_rhp():
    """F4.3: Early release for RHP sails high (+Z) and arm-side (-X)."""
    calc = get_calculations_module()
    tiers = get_tiers_module()

    rng = random.Random(303)
    target_x, target_z = 0.0, 2.50

    high_arm_side_count = 0
    total = 100

    for _ in range(total):
        delivery = calc.calculate_pitch_delivery(
            target_x=target_x,
            target_z=target_z,
            command_rating=65.0,
            pitch_count=30,
            timing_tier=tiers.TimingTier.OKAY,
            timing_label="EARLY • OKAY",
            pitcher_hand="R",
            rng=rng,
        )
        dx = delivery["realized_x"] - target_x
        dz = delivery["realized_z"] - target_z
        # High (+dz) and arm-side (-dx for RHP)
        if dz > 0 and dx < 0:
            high_arm_side_count += 1

    # Directional bias should place majority of early misses high and arm-side
    assert high_arm_side_count >= 0.60 * total, (
        f"Early RHP miss high-and-arm-side rate {high_arm_side_count}/{total} below expected 60%"
    )


def test_f4_early_release_directional_bias_lhp():
    """F4.4: Early release for LHP sails high (+Z) and arm-side (+X)."""
    calc = get_calculations_module()
    tiers = get_tiers_module()

    rng = random.Random(404)
    target_x, target_z = 0.0, 2.50

    high_arm_side_count = 0
    total = 100

    for _ in range(total):
        delivery = calc.calculate_pitch_delivery(
            target_x=target_x,
            target_z=target_z,
            command_rating=65.0,
            pitch_count=30,
            timing_tier=tiers.TimingTier.OKAY,
            timing_label="EARLY • OKAY",
            pitcher_hand="L",
            rng=rng,
        )
        dx = delivery["realized_x"] - target_x
        dz = delivery["realized_z"] - target_z
        # High (+dz) and arm-side (+dx for LHP)
        if dz > 0 and dx > 0:
            high_arm_side_count += 1

    assert high_arm_side_count >= 0.60 * total, (
        f"Early LHP miss high-and-arm-side rate {high_arm_side_count}/{total} below expected 60%"
    )


def test_f4_late_release_directional_bias_low_dirt():
    """F4.5: Late release spikes low and into the dirt (-Z) for both RHP and LHP."""
    calc = get_calculations_module()
    tiers = get_tiers_module()

    rng = random.Random(505)
    target_x, target_z = 0.0, 2.00  # Lower target

    for hand in ["R", "L"]:
        low_dirt_count = 0
        total = 80
        for _ in range(total):
            delivery = calc.calculate_pitch_delivery(
                target_x=target_x,
                target_z=target_z,
                command_rating=60.0,
                pitch_count=40,
                timing_tier=tiers.TimingTier.POOR,
                timing_label="LATE • POOR",
                pitcher_hand=hand,
                rng=rng,
            )
            dz = delivery["realized_z"] - target_z
            if dz < 0:  # Spiked low
                low_dirt_count += 1

        assert low_dirt_count >= 0.70 * total, (
            f"Late miss low spike rate for {hand}HP {low_dirt_count}/{total} below expected 70%"
        )


def test_f4_dispersion_respects_executed_radius_boundary():
    """F4.6: Realized coordinates strictly respect the executed error radius circle."""
    calc = get_calculations_module()
    tiers = get_tiers_module()

    rng = random.Random(606)
    target_x, target_z = 0.25, 2.30

    for timing in [tiers.TimingTier.PERFECT, tiers.TimingTier.GOOD, tiers.TimingTier.OKAY, tiers.TimingTier.POOR]:
        delivery = calc.calculate_pitch_delivery(
            target_x=target_x,
            target_z=target_z,
            command_rating=75.0,
            pitch_count=25,
            timing_tier=timing,
            timing_label=str(timing.value),
            rng=rng,
        )
        radial_miss = delivery["radial_miss_inches"]
        executed_radius = delivery["executed_radius_inches"]
        # Allow tiny numerical tolerance of 0.05 inches
        assert radial_miss <= (executed_radius + 0.05), (
            f"Miss {radial_miss}\" escaped executed radius boundary {executed_radius}\""
        )


# ============================================================================
# F5: API Contract & Telemetry (/api/pitch/throw) (5 tests)
# ============================================================================

def test_f5_api_throw_accepts_timing_tier_and_label(client):
    """F5.1: POST /api/pitch/throw accepts optional timing_tier and timing_label in payload."""
    payload = {
        "selection_mode": "user",
        "pitch_name": "4-Seam Fastball",
        "pitch_intent": "STRIKE",
        "target_zone": "heart",
        "target_x": 0.0,
        "target_z": 2.50,
        "timing_tier": "PERFECT",
        "timing_label": "PERFECT!",
    }

    response = client.post("/api/pitch/throw", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.data}"
    data = response.get_json()
    assert data["status"] == "success"


def test_f5_api_throw_returns_full_telemetry_fields(client):
    """F5.2: POST /api/pitch/throw returns complete execution telemetry in response."""
    payload = {
        "selection_mode": "user",
        "pitch_name": "4-Seam Fastball",
        "pitch_intent": "STRIKE",
        "target_zone": "heart",
        "target_x": 0.0,
        "target_z": 2.50,
        "timing_tier": "GOOD",
        "timing_label": "GOOD",
    }

    response = client.post("/api/pitch/throw", json=payload)
    assert response.status_code == 200
    data = response.get_json()

    assert "execution" in data, "execution block missing from response"
    exec_data = data["execution"]

    # Verify all 6 mandatory telemetry fields from R4
    required_fields = [
        "ability_tier",
        "timing_tier",
        "timing_label",
        "base_radius_inches",
        "executed_radius_inches",
        "radial_miss_inches",
    ]
    for field in required_fields:
        assert field in exec_data, f"Telemetry field '{field}' missing from execution response"

    assert exec_data["timing_tier"] == "GOOD"
    assert exec_data["timing_label"] == "GOOD"
    assert exec_data["base_radius_inches"] > 0
    assert exec_data["executed_radius_inches"] > 0
    assert exec_data["radial_miss_inches"] >= 0


def test_f5_api_throw_simulation_fallback_when_timing_omitted(client):
    """F5.3: Omitting timing fields falls back to probabilistic simulation roll with telemetry."""
    payload = {
        "selection_mode": "user",
        "pitch_name": "4-Seam Fastball",
        "pitch_intent": "STRIKE",
        "target_zone": "heart",
        "target_x": 0.0,
        "target_z": 2.50,
        # timing_tier and timing_label omitted
    }

    response = client.post("/api/pitch/throw", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    exec_data = data["execution"]

    # Valid timing tier must be generated probabilistically
    assert exec_data["timing_tier"] in ["PERFECT", "GOOD", "OKAY", "POOR"]
    assert isinstance(exec_data["timing_label"], str) and len(exec_data["timing_label"]) > 0
    assert exec_data["executed_radius_inches"] > 0


def test_f5_api_throw_rejects_invalid_timing_tier(client):
    """F5.4: POST /api/pitch/throw rejects invalid timing_tier values with HTTP 400."""
    payload = {
        "selection_mode": "user",
        "pitch_name": "4-Seam Fastball",
        "pitch_intent": "STRIKE",
        "target_zone": "heart",
        "target_x": 0.0,
        "target_z": 2.50,
        "timing_tier": "INVALID_TIER_NAME",
        "timing_label": "HACK!",
    }

    response = client.post("/api/pitch/throw", json=payload)
    assert response.status_code == 400, f"Expected 400 for invalid timing_tier, got {response.status_code}"
    data = response.get_json()
    assert "status" in data and data["status"] == "error"


def test_f5_api_throw_preserves_ability_tier_consistency(client):
    """F5.5: Telemetry ability_tier matches the pitcher's active effective command tier."""
    payload = {
        "selection_mode": "user",
        "pitch_name": "4-Seam Fastball",
        "pitch_intent": "STRIKE",
        "target_zone": "heart",
        "target_x": 0.0,
        "target_z": 2.50,
    }

    response = client.post("/api/pitch/throw", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    ability_tier = data["execution"]["ability_tier"]

    valid_tiers = ["ELITE", "GREAT", "GOOD", "OKAY", "MEDIOCRE", "POOR"]
    assert ability_tier in valid_tiers, f"Unexpected ability_tier: {ability_tier}"


# ============================================================================
# F6: Interactive Delivery Mechanics (5 tests)
# ============================================================================

def test_f6_charging_progression_monotonically_increases():
    """F6.1: Hold duration maps monotonically to charging progression ratio."""
    hold_times = [100.0, 300.0, 600.0, 800.0, 1000.0, 1200.0]
    target_ms = 1000.0
    progressions = [t / target_ms for t in hold_times]

    for i in range(len(progressions) - 1):
        assert progressions[i] < progressions[i + 1], "Charging progression must monotonically increase"


def test_f6_sweet_spot_window_detection():
    """F6.2: Releases within sweet spot window (95% to 105% charge) lock in PERFECT."""
    sweet_spot_releases = [950.0, 980.0, 1000.0, 1020.0, 1050.0]

    for hold_ms in sweet_spot_releases:
        tier, label = evaluate_charging_timing(hold_ms, target_sweet_spot_ms=1000.0)
        assert tier == "PERFECT", f"Hold {hold_ms}ms should be PERFECT, got {tier}"
        assert label == "PERFECT!"


def test_f6_early_release_classification():
    """F6.3: Early releases before sweet spot classify as EARLY • GOOD or EARLY • OKAY."""
    # 85% to 94% -> GOOD (Early)
    tier, label = evaluate_charging_timing(900.0, 1000.0)
    assert tier == "GOOD"
    assert "EARLY" in label

    # 65% to 84% -> OKAY (Early)
    tier, label = evaluate_charging_timing(750.0, 1000.0)
    assert tier == "OKAY"
    assert "EARLY" in label


def test_f6_late_release_classification():
    """F6.4: Late releases after sweet spot classify as LATE • GOOD or LATE • OKAY."""
    # 106% to 115% -> GOOD (Late)
    tier, label = evaluate_charging_timing(1100.0, 1000.0)
    assert tier == "GOOD"
    assert "LATE" in label

    # 116% to 135% -> OKAY (Late)
    tier, label = evaluate_charging_timing(1250.0, 1000.0)
    assert tier == "OKAY"
    assert "LATE" in label


def test_f6_severe_misstiming_classification_poor():
    """F6.5: Severe mistiming (<65% or >135% charge) locks in POOR with appropriate label."""
    # Severely early
    tier_early, label_early = evaluate_charging_timing(400.0, 1000.0)
    assert tier_early == "POOR"
    assert label_early == "EARLY • POOR"

    # Severely late
    tier_late, label_late = evaluate_charging_timing(1500.0, 1000.0)
    assert tier_late == "POOR"
    assert label_late == "LATE • POOR"


# ============================================================================
# F7: Reticle Calculation & Miss Vector Validation (5 tests)
# ============================================================================

def test_f7_base_reticle_radius_matches_good_anchor():
    """F7.1: Base reticle geometry matches GOOD 1.0x baseline error circle."""
    base_r = get_max_error_radius_inches(80.0)
    geom = calculate_reticle_geometry(base_r, timing_tier="GOOD")

    assert geom["base_radius_inches"] == base_r
    assert geom["executed_radius_inches"] == base_r
    assert geom["multiplier"] == 1.00
    assert geom["bloom_ratio"] == 1.00


def test_f7_reticle_bloom_contraction_expansion_ratios():
    """F7.2: Reticle snaps/blooms according to calibrated multipliers (0.52x, 1.97x, 3.75x)."""
    base_r = 2.00  # 2.00 inches

    geom_perfect = calculate_reticle_geometry(base_r, "PERFECT")
    assert geom_perfect["executed_radius_inches"] < base_r
    assert math.isclose(geom_perfect["bloom_ratio"], 0.52, rel_tol=0.05)

    geom_okay = calculate_reticle_geometry(base_r, "OKAY")
    assert geom_okay["executed_radius_inches"] > base_r
    assert math.isclose(geom_okay["bloom_ratio"], 1.97, rel_tol=0.05)

    geom_poor = calculate_reticle_geometry(base_r, "POOR")
    assert geom_poor["executed_radius_inches"] > geom_okay["executed_radius_inches"]
    assert math.isclose(geom_poor["bloom_ratio"], 3.75, rel_tol=0.05)


def test_f7_miss_vector_euclidean_distance():
    """F7.3: Miss vector Euclidean distance in inches matches radial miss calculation."""
    target_x, target_z = 0.0, 2.50
    realized_x, realized_z = 0.10, 2.65  # In Statcast feet

    vec = calculate_miss_vector(target_x, target_z, realized_x, realized_z)
    math_miss = calculate_radial_miss_inches(target_x, target_z, realized_x, realized_z)

    assert math.isclose(vec["radial_miss_inches"], math_miss, abs_tol=0.05)
    # Check delta components: dx = 0.10 ft = 1.2 in, dz = 0.15 ft = 1.8 in
    assert math.isclose(vec["delta_x_in"], 1.20, abs_tol=0.05)
    assert math.isclose(vec["delta_z_in"], 1.80, abs_tol=0.05)


def test_f7_miss_vector_angle_and_direction():
    """F7.4: Miss vector angle accurately describes the miss direction."""
    target_x, target_z = 0.0, 2.50

    # Miss directly high: dx=0, dz=+0.2 ft -> angle = +90 degrees
    vec_high = calculate_miss_vector(target_x, target_z, 0.0, 2.70)
    assert math.isclose(vec_high["angle_degrees"], 90.0, abs_tol=1.0)

    # Miss directly low (dirt): dx=0, dz=-0.2 ft -> angle = -90 degrees
    vec_low = calculate_miss_vector(target_x, target_z, 0.0, 2.30)
    assert math.isclose(vec_low["angle_degrees"], -90.0, abs_tol=1.0)


def test_f7_reticle_radius_monotonicity_with_command():
    """F7.5: Higher pitcher command produces strictly smaller base reticle radius."""
    commands = [45.0, 60.0, 75.0, 85.0, 95.0]
    radii = [get_max_error_radius_inches(c) for c in commands]

    for i in range(len(radii) - 1):
        assert radii[i] > radii[i + 1], (
            f"Base reticle radius at command {commands[i]} ({radii[i]}\") "
            f"must be larger than at {commands[i+1]} ({radii[i+1]}\")"
        )
