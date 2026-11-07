"""
Tier 4: Real-World Application Scenarios Test Suite.
Validates multi-pitch at-bats, inning sequences, fatigue progression, and interactive API gameplay (Total: 6 tests).
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
)
from backend.engine.game_engine.gameday_math import (
    get_max_error_radius_inches,
)


def test_f4_scenario_ace_shutdown_inning():
    """Scenario 1: Ace shutdown inning (3 consecutive outs, low pitch count, ELITE ability tier).
    Simulates an elite starter dominating a frame with tight command and minimal radial miss.
    """
    tiers = get_tiers_module()
    adj = get_adjusted_ratings_module()
    calc = get_calculations_module()

    ace_command = 93.0
    ace_stamina = 85.0
    ace_composure = 90.0

    # 3-batter inning: sequence of 9 pitches
    pitch_sequence = [
        # Batter 1: 3 pitches
        ("4SFB", 0.0, 2.5, tiers.TimingTier.PERFECT, "PERFECT!"),
        ("SL", 0.4, 2.2, tiers.TimingTier.GOOD, "GOOD"),
        ("4SFB", -0.4, 3.2, tiers.TimingTier.PERFECT, "PERFECT!"),
        # Batter 2: 3 pitches
        ("CH", 0.0, 1.8, tiers.TimingTier.GOOD, "GOOD"),
        ("4SFB", 0.3, 2.8, tiers.TimingTier.PERFECT, "PERFECT!"),
        ("SL", 0.5, 1.9, tiers.TimingTier.PERFECT, "PERFECT!"),
        # Batter 3: 3 pitches
        ("4SFB", 0.0, 2.5, tiers.TimingTier.GOOD, "GOOD"),
        ("CB", 0.0, 1.6, tiers.TimingTier.PERFECT, "PERFECT!"),
        ("4SFB", 0.0, 3.4, tiers.TimingTier.PERFECT, "PERFECT!"),
    ]

    rng = random.Random(4001)

    for i, (pitch_type, tx, tz, timing, label) in enumerate(pitch_sequence):
        pitch_num = i + 1
        eff_cmd, tier = adj.compute_effective_command(
            base_command=ace_command,
            pitch_type=pitch_type,
            pitch_count=pitch_num,
            stamina=ace_stamina,
            composure=ace_composure,
            consistency=85.0,
            is_leverage=False,
        )

        # Ace remains in ELITE, GREAT, or GOOD (for secondary breaking balls like CB) tier throughout the shutdown inning
        assert tier in (tiers.AbilityTier.ELITE, tiers.AbilityTier.GREAT, tiers.AbilityTier.GOOD)
        assert eff_cmd >= 75.0

        delivery = calc.calculate_pitch_delivery(
            target_x=tx,
            target_z=tz,
            command_rating=eff_cmd,
            pitch_count=pitch_num,
            stamina=ace_stamina,
            timing_tier=timing,
            timing_label=label,
            pitch_type=pitch_type,
            rng=rng,
        )

        # Executed radius remains sharp (< 2.65")
        assert delivery["executed_radius_inches"] <= 2.65
        # Ace executes with minimal radial miss
        assert delivery["radial_miss_inches"] <= 2.25


def test_f4_scenario_bases_loaded_high_leverage_jam():
    """Scenario 2: High-leverage bases loaded jam (3-2 full count, 2 outs).
    Tests composure stress, dynamic shift in simulation distribution, and delivery under pressure.
    """
    tiers = get_tiers_module()
    adj = get_adjusted_ratings_module()
    calc = get_calculations_module()

    base_cmd = 78.0  # GOOD pitcher
    stamina = 75.0
    pitch_count = 65

    # 1. Neutral state
    cmd_neutral, tier_neutral = adj.compute_effective_command(
        base_command=base_cmd,
        pitch_type="4SFB",
        pitch_count=pitch_count,
        stamina=stamina,
        composure=50.0,
        consistency=60.0,
        is_leverage=False,
    )

    # 2. Bases loaded high leverage state
    cmd_jam, tier_jam = adj.compute_effective_command(
        base_command=base_cmd,
        pitch_type="4SFB",
        pitch_count=pitch_count,
        stamina=stamina,
        composure=50.0,
        consistency=60.0,
        is_leverage=True,
    )

    # Leverage stress reduces effective command
    assert cmd_jam < cmd_neutral

    # 3. Simulation distribution shifts towards OKAY / POOR
    dist_neutral = calc.get_simulation_timing_distribution(
        ability_tier=tier_neutral.value if hasattr(tier_neutral, "value") else tier_neutral,
        composure=50.0,
        consistency=60.0,
        pitch_count=pitch_count,
        stamina=stamina,
        is_leverage=False,
    )
    dist_jam = calc.get_simulation_timing_distribution(
        ability_tier=tier_jam.value if hasattr(tier_jam, "value") else tier_jam,
        composure=50.0,
        consistency=60.0,
        pitch_count=pitch_count,
        stamina=stamina,
        is_leverage=True,
    )

    miss_prob_neutral = dist_neutral["OKAY"] + dist_neutral["POOR"]
    miss_prob_jam = dist_jam["OKAY"] + dist_jam["POOR"]
    assert miss_prob_jam > miss_prob_neutral, "Jam situation must increase miss probability"


def test_f4_scenario_starter_fatigue_deterioration_multi_inning():
    """Scenario 3: Starter running out of gas (fatigue progression from pitch 15 to 105).
    Verifies gradual widening of reticle and degradation of ability tier over pitch count.
    """
    tiers = get_tiers_module()
    adj = get_adjusted_ratings_module()

    base_cmd = 84.0  # GREAT tier starter
    stamina = 75.0
    composure = 75.0
    consistency = 75.0

    milestones = [15, 50, 80, 105]
    results = []

    for pc in milestones:
        eff_cmd, tier = adj.compute_effective_command(
            base_command=base_cmd,
            pitch_type="4SFB",
            pitch_count=pc,
            stamina=stamina,
            composure=composure,
            consistency=consistency,
        )
        base_r = get_max_error_radius_inches(eff_cmd)
        results.append((pc, eff_cmd, tier, base_r))

    # Milestones verification:
    # Pitch 15: Fresh (GREAT tier, base_r ~1.4")
    assert results[0][2] == tiers.AbilityTier.GREAT
    # Pitch 50: Settled (GREAT tier)
    assert results[1][2] == tiers.AbilityTier.GREAT
    # Pitch 80: Past stamina (Degrades to GOOD tier, base_r > 2.0")
    assert results[2][1] < results[1][1]
    # Pitch 105: Fatigued (Degrades further to GOOD, OKAY or MEDIOCRE)
    assert results[3][1] < results[2][1]
    assert results[3][2] in (tiers.AbilityTier.GOOD, tiers.AbilityTier.OKAY, tiers.AbilityTier.MEDIOCRE)

    # Reticle radius must monotonically widen
    for i in range(len(results) - 1):
        assert results[i][3] <= results[i + 1][3], (
            f"Reticle at pitch {results[i][0]} ({results[i][3]}\") "
            f"should be <= pitch {results[i+1][0]} ({results[i+1][3]}\")"
        )


def test_f4_scenario_tactical_arsenal_rotation_at_bat():
    """Scenario 4: Tactical 6-pitch at-bat sequence with dynamic difficulty adaptation.
    Re-evaluates effective command per pitch based on pitch type modifiers (4SFB, SL, 2SFB, CB, CH, KN).
    """
    tiers = get_tiers_module()
    adj = get_adjusted_ratings_module()

    base_cmd = 80.0
    stamina = 80.0

    at_bat_pitches = [
        ("4SFB", 1.00),
        ("SL", 1.15),
        ("2SFB", 1.02),
        ("CB", 1.20),
        ("CH", 1.08),
        ("KN", 1.35),
    ]

    commands = {}
    for pitch, mod in at_bat_pitches:
        eff_cmd, _ = adj.compute_effective_command(
            base_command=base_cmd,
            pitch_type=pitch,
            pitch_count=45,
            stamina=stamina,
            composure=75.0,
            consistency=75.0,
        )
        commands[pitch] = eff_cmd

    # Fastball has highest effective command, Knuckleball has lowest
    assert commands["4SFB"] > commands["2SFB"] > commands["CH"] > commands["SL"] > commands["CB"] > commands["KN"]


def test_f4_scenario_interactive_user_gameplay_at_bat_via_api(client):
    """Scenario 5: Full at-bat with interactive user timing via API.
    Simulates 3 consecutive pitches with user release timing, state resolution, and telemetry checks.
    """
    # Pitch 1: Fastball to heart with PERFECT release
    p1_tier, p1_label = evaluate_charging_timing(1000.0, 1000.0)
    res1 = client.post("/api/pitch/throw", json={
        "selection_mode": "user",
        "pitch_name": "4-Seam Fastball",
        "pitch_intent": "STRIKE",
        "target_zone": "heart",
        "target_x": 0.0,
        "target_z": 2.50,
        "timing_tier": p1_tier,
        "timing_label": p1_label,
    })
    assert res1.status_code == 200
    p1_data = res1.get_json()
    assert p1_data["execution"]["timing_tier"] == "PERFECT"

    # Resolve Pitch 1 (Called strike)
    resolve1 = client.post("/api/pitch/resolve", json={"batter_decision": "TAKE"})
    assert resolve1.status_code == 200

    # Pitch 2: Slider chasing away with EARLY • GOOD release
    p2_tier, p2_label = evaluate_charging_timing(890.0, 1000.0)
    res2 = client.post("/api/pitch/throw", json={
        "selection_mode": "user",
        "pitch_name": "Slider",
        "pitch_intent": "CHASE",
        "target_zone": "chase-away",
        "target_x": 1.05,
        "target_z": 2.20,
        "timing_tier": p2_tier,
        "timing_label": p2_label,
    })
    assert res2.status_code == 200
    p2_data = res2.get_json()
    assert p2_data["execution"]["timing_tier"] == "GOOD"

    # Resolve Pitch 2 (Swinging strike)
    resolve2 = client.post("/api/pitch/resolve", json={"batter_decision": "SWING"})
    assert resolve2.status_code == 200

    # Pitch 3: Curveball with LATE • POOR release (spiked)
    p3_tier, p3_label = evaluate_charging_timing(1450.0, 1000.0)
    res3 = client.post("/api/pitch/throw", json={
        "selection_mode": "user",
        "pitch_name": "Curveball",
        "pitch_intent": "WASTE",
        "target_zone": "chase-low",
        "target_x": 0.0,
        "target_z": 1.15,
        "timing_tier": p3_tier,
        "timing_label": p3_label,
    })
    assert res3.status_code == 200
    p3_data = res3.get_json()
    assert p3_data["execution"]["timing_tier"] == "POOR"
    assert p3_data["execution"]["executed_radius_inches"] > p1_data["execution"]["executed_radius_inches"]

    # Resolve Pitch 3 (Batter takes ball)
    resolve3 = client.post("/api/pitch/resolve", json={"batter_decision": "TAKE"})
    assert resolve3.status_code == 200


def test_f4_scenario_bullpen_reliever_leverage_entry():
    """Scenario 6: Bullpen reliever enters with RISP in late inning.
    Lower stamina (35) degrades rapidly, but high composure (85) maintains command in early pitches.
    """
    tiers = get_tiers_module()
    adj = get_adjusted_ratings_module()

    reliever_cmd = 80.0
    reliever_stamina = 35.0  # Bullpen profile
    reliever_composure = 85.0

    # Pitch 5: Reliever is sharp, holding runners in check
    cmd_p5, tier_p5 = adj.compute_effective_command(
        base_command=reliever_cmd,
        pitch_type="4SFB",
        pitch_count=5,
        stamina=reliever_stamina,
        composure=reliever_composure,
        consistency=75.0,
        is_leverage=True,
    )
    assert tier_p5 in (tiers.AbilityTier.GREAT, tiers.AbilityTier.GOOD)

    # Pitch 45: Reliever pushed beyond bullpen capacity (45 pitches on 35 stamina)
    cmd_p45, tier_p45 = adj.compute_effective_command(
        base_command=reliever_cmd,
        pitch_type="4SFB",
        pitch_count=45,
        stamina=reliever_stamina,
        composure=reliever_composure,
        consistency=75.0,
        is_leverage=True,
    )

    # Fatigue rapidly degrades reliever's effective command
    assert cmd_p45 < cmd_p5 - 8.0
    assert tier_p45 in (tiers.AbilityTier.OKAY, tiers.AbilityTier.MEDIOCRE, tiers.AbilityTier.POOR)
