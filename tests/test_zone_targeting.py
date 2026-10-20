"""Regression tests for ball-zone targeting and corner classification."""

from backend.api.app import create_app
from backend.engine.gameday_math import (
    CHASE_BORDER_FT,
    classify_gameday_zone,
    get_max_error_radius_inches,
    get_zone_nominal_target,
    is_rulebook_strike,
)
from backend.engine.pitching_engine.calculations import calculate_pitch_delivery

CHASE_ZONES = ("chase-high", "chase-low", "chase-in", "chase-away")


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
