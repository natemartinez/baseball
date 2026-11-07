"""
Tier 3: Cross-Feature Combinations Test Suite.
Validates multi-variable pairwise and combinatorial interactions across Features F1-F7 (Total: 8 tests).
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
    classify_gameday_zone,
)


def test_f3_combo_poor_pitcher_knuckleball_high_leverage_late_release():
    """Combo 1: Poor pitcher throwing Knuckleball under high leverage with late release.
    Combines F1 (ratings/modifiers), F2 (radius scaling), F4 (dispersion), F7 (miss vector).
    """
    tiers = get_tiers_module()
    adj = get_adjusted_ratings_module()
    calc = get_calculations_module()

    # 1. Pitcher rating under stress & KN modifier
    eff_cmd, tier = adj.compute_effective_command(
        base_command=45.0,  # POOR
        pitch_type="KN",    # 1.35x modifier
        pitch_count=75,     # Fatigue
        stamina=50.0,
        composure=35.0,     # Shaky
        consistency=40.0,
        is_leverage=True,
    )
    assert tier == tiers.AbilityTier.POOR
    assert eff_cmd < 40.0

    # 2. Base error radius clamps to max 10.50"
    base_r = get_max_error_radius_inches(eff_cmd)
    assert math.isclose(base_r, 10.50, abs_tol=1e-3)

    # 3. Delivery execution with LATE POOR release
    rng = random.Random(111)
    target_x, target_z = 0.0, 2.00
    delivery = calc.calculate_pitch_delivery(
        target_x=target_x,
        target_z=target_z,
        command_rating=eff_cmd,
        pitch_count=75,
        stamina=50.0,
        timing_tier=tiers.TimingTier.POOR,
        timing_label="LATE • POOR",
        pitch_type="KN",
        rng=rng,
    )

    # Executed radius blooms ~3.75x (10.50 * 3.75 = 39.375)
    assert math.isclose(delivery["executed_radius_inches"], 39.375, abs_tol=0.2)
    # Late miss directional spike into dirt (-Z)
    assert delivery["realized_z"] < target_z
    assert delivery["radial_miss_inches"] <= 39.375 + 0.1


def test_f3_combo_elite_pitcher_slider_perfect_timing():
    """Combo 2: Elite pitcher throwing Slider with Perfect release.
    Combines F1 (ratings), F2 (contraction), F4 (center clustering), F7 (reticle).
    """
    tiers = get_tiers_module()
    adj = get_adjusted_ratings_module()
    calc = get_calculations_module()

    eff_cmd, tier = adj.compute_effective_command(
        base_command=95.0,
        pitch_type="SL",    # 1.15x modifier
        pitch_count=15,
        stamina=85.0,
        composure=90.0,
        consistency=85.0,
        is_leverage=False,
    )
    assert tier in (tiers.AbilityTier.ELITE, tiers.AbilityTier.GREAT)
    assert eff_cmd >= 82.0

    base_r = get_max_error_radius_inches(eff_cmd)
    assert base_r <= 2.25

    rng = random.Random(222)
    delivery = calc.calculate_pitch_delivery(
        target_x=0.45,
        target_z=2.20,
        command_rating=eff_cmd,
        pitch_count=15,
        stamina=85.0,
        timing_tier=tiers.TimingTier.PERFECT,
        timing_label="PERFECT!",
        pitch_type="SL",
        rng=rng,
    )

    # Contracted radius: <= 2.25 * 0.52 = ~1.17"
    assert delivery["executed_radius_inches"] <= 1.25
    assert delivery["radial_miss_inches"] <= delivery["executed_radius_inches"] + 0.05
    assert delivery["radial_miss_inches"] < 1.10


def test_f3_combo_mediocre_pitcher_changeup_early_okay_release_lhp():
    """Combo 3: LHP Mediocre pitcher throwing Changeup with Early Okay release.
    Combines F1 (ratings), F2 (scaling), F4 (handedness-aware early high/arm-side).
    """
    tiers = get_tiers_module()
    adj = get_adjusted_ratings_module()
    calc = get_calculations_module()

    eff_cmd, tier = adj.compute_effective_command(
        base_command=56.0,
        pitch_type="CH",
        pitch_count=40,
        stamina=65.0,
        composure=60.0,
        consistency=55.0,
        is_leverage=False,
    )
    assert tier in (tiers.AbilityTier.MEDIOCRE, tiers.AbilityTier.OKAY)

    target_x, target_z = 0.0, 2.50
    rng = random.Random(333)
    delivery = calc.calculate_pitch_delivery(
        target_x=target_x,
        target_z=target_z,
        command_rating=eff_cmd,
        pitch_count=40,
        stamina=65.0,
        timing_tier=tiers.TimingTier.OKAY,
        timing_label="EARLY • OKAY",
        pitcher_hand="L",
        pitch_type="CH",
        rng=rng,
    )

    # LHP early miss sails high (+dz) and arm-side (+dx for LHP)
    dx = delivery["realized_x"] - target_x
    dz = delivery["realized_z"] - target_z
    assert dz > 0, f"Early release must sail high: dz={dz}"
    assert dx > 0, f"Early release for LHP must sail arm-side (+X): dx={dx}"


def test_f3_combo_great_pitcher_fatigued_2sfb_high_leverage_good_timing():
    """Combo 4: Great pitcher fatigued throwing 2SFB under high leverage with Good timing.
    Combines F1 (fatigue demotion), F2 (identity scaling), F5 (telemetry agreement).
    """
    tiers = get_tiers_module()
    adj = get_adjusted_ratings_module()
    calc = get_calculations_module()

    eff_cmd, tier = adj.compute_effective_command(
        base_command=86.0,  # GREAT
        pitch_type="2SFB",  # 1.02x modifier
        pitch_count=90,     # Heavy fatigue
        stamina=72.0,
        composure=70.0,
        consistency=75.0,
        is_leverage=True,
    )
    # Fatigue drops effective command into GOOD tier
    assert tier == tiers.AbilityTier.GOOD
    assert 70.0 <= eff_cmd < 80.0

    base_r = get_max_error_radius_inches(eff_cmd)
    delivery = calc.calculate_pitch_delivery(
        target_x=-0.35,
        target_z=2.10,
        command_rating=eff_cmd,
        pitch_count=90,
        stamina=72.0,
        timing_tier=tiers.TimingTier.GOOD,
        timing_label="GOOD",
        pitch_type="2SFB",
    )

    # Executed radius equals base radius for GOOD timing
    assert math.isclose(delivery["executed_radius_inches"], base_r, rel_tol=1e-3)


def test_f3_combo_good_pitcher_curveball_late_poor_dirt():
    """Combo 5: Good pitcher throwing Curveball with Late Poor timing into the dirt.
    Combines F1 (difficulty modifier), F2 (POOR bloom), F4 (dirt miss), zone classification.
    """
    tiers = get_tiers_module()
    calc = get_calculations_module()

    target_x, target_z = 0.0, 1.80  # Low target
    delivery = calc.calculate_pitch_delivery(
        target_x=target_x,
        target_z=target_z,
        command_rating=75.0,
        pitch_count=35,
        stamina=75.0,
        timing_tier=tiers.TimingTier.POOR,
        timing_label="LATE • POOR",
        pitch_type="CB",
        rng=random.Random(555),
    )

    # Pitch spikes below rulebook zone bottom (< 1.50 ft)
    assert delivery["realized_z"] < 1.50
    zone = classify_gameday_zone(delivery["realized_x"], delivery["realized_z"])
    assert zone in ("CHASE", "WASTE"), f"Spiked curveball expected CHASE/WASTE, got {zone}"


def test_f3_combo_elite_pitcher_cutter_100_pitches_perfect_timing():
    """Combo 6: Elite pitcher at 100 pitches throwing Cutter with Perfect timing.
    Combines F1 (deep fatigue), F2 (PERFECT contraction overcomes fatigue widening).
    """
    tiers = get_tiers_module()
    adj = get_adjusted_ratings_module()
    calc = get_calculations_module()

    eff_cmd, _ = adj.compute_effective_command(
        base_command=92.0,
        pitch_type="CUT",
        pitch_count=100,
        stamina=80.0,
        composure=85.0,
        consistency=80.0,
    )
    base_r = get_max_error_radius_inches(eff_cmd)

    delivery = calc.calculate_pitch_delivery(
        target_x=0.40,
        target_z=3.00,
        command_rating=eff_cmd,
        pitch_count=100,
        stamina=80.0,
        timing_tier=tiers.TimingTier.PERFECT,
        timing_label="PERFECT!",
        pitch_type="CUT",
    )

    # Perfect contraction contracts the fatigued base radius down by ~0.52x
    assert delivery["executed_radius_inches"] < base_r
    assert math.isclose(delivery["executed_radius_inches"] / base_r, 0.52, rel_tol=0.05)


def test_f3_combo_poor_pitcher_splitter_early_okay_rhp():
    """Combo 7: RHP Poor pitcher throwing Splitter with Early Okay timing.
    Combines F1 (SPL 1.25x), F2 (OKAY 1.97x), F4 (RHP high and arm-side).
    """
    tiers = get_tiers_module()
    calc = get_calculations_module()

    target_x, target_z = 0.0, 2.50
    delivery = calc.calculate_pitch_delivery(
        target_x=target_x,
        target_z=target_z,
        command_rating=48.0,
        pitch_count=50,
        timing_tier=tiers.TimingTier.OKAY,
        timing_label="EARLY • OKAY",
        pitcher_hand="R",
        pitch_type="SPL",
        rng=random.Random(777),
    )

    # RHP early miss: dz > 0 (high), dx < 0 (arm-side)
    assert delivery["realized_z"] > target_z
    assert delivery["realized_x"] < target_x


def test_f3_combo_interactive_delivery_to_api_roundtrip(client):
    """Combo 8: Interactive UI mechanic charging roundtrips through API throw endpoint.
    Combines F6 (press-and-release charging), F5 (API contract), F2 & F7 (telemetry validation).
    """
    # 1. User holds THROW button for 990ms (within 950-1050ms sweet spot)
    tier, label = evaluate_charging_timing(hold_time_ms=990.0, target_sweet_spot_ms=1000.0)
    assert tier == "PERFECT"
    assert label == "PERFECT!"

    # 2. Dispatch payload with timing locked by interactive mechanic
    payload = {
        "selection_mode": "user",
        "pitch_name": "Slider",
        "pitch_intent": "CHASE",
        "target_zone": "chase-away",
        "target_x": 1.05,
        "target_z": 2.20,
        "timing_tier": tier,
        "timing_label": label,
    }

    response = client.post("/api/pitch/throw", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    exec_data = data["execution"]

    # 3. Telemetry matches user interaction
    assert exec_data["timing_tier"] == "PERFECT"
    assert exec_data["timing_label"] == "PERFECT!"
    # Contracted radius matches base * 0.52
    assert math.isclose(
        exec_data["executed_radius_inches"] / exec_data["base_radius_inches"],
        0.52,
        rel_tol=0.05,
    )
