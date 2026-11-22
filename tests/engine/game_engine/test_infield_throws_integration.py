"""
Integration tests for Infield Throws, Batter-Runner Timing, and Contact Outcome Telemetry.
"""

import pytest
from backend.engine.batting_engine.contact.contact_outcome import resolve_contact_outcome
from backend.engine.game_engine.defense import ActiveDefense


def test_routine_groundout_to_ss_has_throw_telemetry():
    # 90 mph grounder at 0 deg launch, -15 spray to SS
    res = resolve_contact_outcome(90.0, 0.0, -15.0, batter_speed=65.0)
    assert res is not None
    assert res["call"] == "IN_PLAY_OUT"
    batted = res["batted_ball"]
    assert "throw" in batted
    throw_data = batted["throw"]
    assert throw_data is not None
    assert throw_data["thrower_id"] == "SS"
    assert throw_data["target_base"] == "1B"
    assert throw_data["is_out"] is True
    assert len(throw_data["samples"]) == 10
    assert throw_data["ball_arrival_time_s"] < throw_data["runner_arrival_time_s"]


def test_deep_chopper_with_elite_runner_becomes_infield_single():
    # Slow chopper deep in SS hole: 60 mph, 2 deg launch, -25 spray
    # With elite batter speed 98, runner beats throw; with speed 65, runner is out
    res_out = resolve_contact_outcome(60.0, 2.0, -25.0, batter_speed=65.0)
    assert res_out["call"] == "IN_PLAY_OUT"
    assert res_out["batted_ball"]["throw"]["is_out"] is True

    res_single = resolve_contact_outcome(60.0, 2.0, -25.0, batter_speed=98.0)
    assert res_single["call"] == "SINGLE"
    assert "Infield single" in res_single["description"] or "beats the throw" in res_single["description"]
    batted = res_single["batted_ball"]
    assert "throw" in batted
    assert batted["throw"] is not None
    assert batted["throw"]["is_out"] is False
    assert batted["throw"]["runner_arrival_time_s"] < batted["throw"]["ball_arrival_time_s"]


def test_airborne_flyout_does_not_generate_infield_throw():
    # 95 mph fly ball caught airborne by CF
    res = resolve_contact_outcome(95.0, 30.0, 0.0, batter_speed=70.0)
    assert res is not None
    assert res["call"] == "IN_PLAY_OUT"
    assert res["batted_ball"]["throw"] is None
