"""Regression tests for ball-zone targeting and corner classification."""

import random

import pytest

from backend.api.app import create_app
from backend.engine.game_engine.gameday_math import (
    CHASE_BORDER_FT,
    ZONE_TARGET_BOUNDS,
    classify_gameday_zone,
    get_max_error_radius_inches,
    get_zone_nominal_target,
    is_rulebook_strike,
    sample_zone_target,
)
from backend.engine.pitching_engine.pitch_execution.calculations import calculate_pitch_delivery

CHASE_ZONES = ("chase-high", "chase-low", "chase-in", "chase-away")
INNER_ZONES = tuple(name for name in ZONE_TARGET_BOUNDS if name not in CHASE_ZONES)


def test_chase_nominal_targets_are_balls():
    for zone in CHASE_ZONES:
        x, z, category = get_zone_nominal_target(zone)
        assert category == "CHASE", zone
        assert not is_rulebook_strike(x, z), zone


def test_corner_bands_match_the_rectangular_classifier():
    # Just outside both the top and glove-side edges: still the shadow band.
    assert classify_gameday_zone(-0.90, 3.60) == "SHADOW"
    # Past one ball width on both edges, but inside two ball widths: chase.
    assert classify_gameday_zone(-1.00, 3.90) == "CHASE"
    # Beyond the chase border: waste.
    assert classify_gameday_zone(-1.30, 4.10) == "WASTE"


def test_chase_centers_cannot_produce_a_rulebook_strike_at_82_command():
    assert get_max_error_radius_inches(82) == 1.5
    for zone in CHASE_ZONES:
        x, z, _ = get_zone_nominal_target(zone)
        for _ in range(500):
            delivery = calculate_pitch_delivery(
                target_x=x,
                target_z=z,
                command_rating=82,
                pitch_count=0,
                stamina=70,
                intended_zone_cat="CHASE",
            )
            assert not delivery["is_strike"], zone


def test_chase_border_is_two_ball_widths_outside_the_zone():
    assert CHASE_BORDER_FT > 0
    # The outer corners of the chase band are balls, not strikes.
    for x, z in (
        (-0.7083 - CHASE_BORDER_FT, 3.5 + CHASE_BORDER_FT),
        (0.7083 + CHASE_BORDER_FT, 1.5 - CHASE_BORDER_FT),
    ):
        assert not is_rulebook_strike(x, z)


def test_custom_chase_targets_are_balls_end_to_end():
    client = create_app().test_client()
    client.post("/api/start_game", json={"home_team_id": 1, "away_team_id": 2})

    for zone in CHASE_ZONES:
        x, z, _ = get_zone_nominal_target(zone)
        for _ in range(5):
            response = client.post(
                "/api/pitch",
                json={
                    "pitch_intent": "STRIKE",
                    "target_x": x,
                    "target_z": z,
                },
            )
            assert response.status_code == 200
            payload = response.get_json()
            packet = payload["pitch_details"]["gameday_packet"]
            assert packet["result"]["isStrike"] is False, (zone, packet["execution"])
            assert payload["pitch_details"]["actual_zone"].startswith("chase-"), (
                zone,
                payload["pitch_details"]["actual_zone"],
            )


@pytest.mark.parametrize("zone", INNER_ZONES)
def test_inner_zone_targets_land_inside_the_single_rectangle(zone):
    random.seed(11)
    for _ in range(500):
        x, z, _ = sample_zone_target(zone)
        assert is_rulebook_strike(x, z), (zone, x, z)


@pytest.mark.parametrize("zone", INNER_ZONES)
def test_inner_zone_target_bounds_include_the_edge(zone):
    x_min, x_max, z_min, z_max = ZONE_TARGET_BOUNDS[zone]
    for rx, rz in ((0.0, 0.0), (1.0, 1.0)):
        values = iter([rx, rz])
        x, z, _ = sample_zone_target(zone, rng=lambda: next(values))
        assert x == pytest.approx(x_min if rx == 0.0 else x_max)
        assert z == pytest.approx(z_min if rz == 0.0 else z_max)
        assert is_rulebook_strike(x, z), (zone, x, z)


@pytest.mark.parametrize("zone", CHASE_ZONES)
def test_chase_zone_targets_always_land_outside_the_rectangle(zone):
    random.seed(12)
    for _ in range(500):
        x, z, category = sample_zone_target(zone)
        assert not is_rulebook_strike(x, z), (zone, x, z)
        assert category == "CHASE", (zone, x, z, category)
