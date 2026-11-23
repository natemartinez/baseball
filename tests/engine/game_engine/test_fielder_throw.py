"""
Unit tests for Fielder Throw Kinematics and 3D Flight Trajectory.
"""

import math
import pytest
from backend.engine.models.player import Player
from backend.engine.game_engine.physics.fielder_throw import (
    BASE_COORDINATES,
    ThrowResult,
    calculate_transfer_time,
    solve_fielder_throw,
)


def test_base_coordinates_match_standard_diamond():
    assert BASE_COORDINATES["HOME"] == (0.0, 0.0, 0.0)
    assert BASE_COORDINATES["1B"] == (63.64, 63.64, 3.0)
    assert BASE_COORDINATES["2B"] == (0.0, 127.28, 3.0)
    assert BASE_COORDINATES["3B"] == (-63.64, 63.64, 3.0)


def test_transfer_time_with_fielding_type_and_body_control():
    # Routine ground scoop with 50 transfer speed: 0.85 - 0.50 * 0.40 = 0.65s
    t_routine = calculate_transfer_time(50.0, fielding_type="GROUND_SCOOP", body_control=65.0)
    assert pytest.approx(t_routine, abs=1e-3) == 0.650

    # Elite transfer speed (100) -> 0.45s
    t_elite = calculate_transfer_time(100.0, fielding_type="GROUND_SCOOP", body_control=80.0)
    assert pytest.approx(t_elite, abs=1e-3) == 0.450

    # Diving stop has recovery penalty
    t_dive = calculate_transfer_time(50.0, fielding_type="DIVING_CATCH", body_control=50.0)
    assert t_dive > t_routine


def test_1b_unassisted_step_when_within_12_ft():
    # 1B fields ball at (60.0, 60.0), which is ~5.1 ft from 1B bag (63.64, 63.64)
    res = solve_fielder_throw(
        fielder_id="1B",
        intercept_x=60.0,
        intercept_y=60.0,
        intercept_z=0.0,
        t_intercept=1.80,
        arm_strength=65.0,
        arm_accuracy=65.0,
        transfer_speed=65.0,
        body_control=65.0,
        fielding_type="GROUND_SCOOP",
        target_base="1B",
        sprint_speed=26.0,
    )
    assert res.is_unassisted is True
    assert res.throw_distance_ft < 12.0
    assert res.ball_arrival_time_s > 1.80
    assert len(res.samples) == 10
    assert res.samples[-1][0] == pytest.approx(63.64, abs=0.1)


def test_ss_deep_throw_to_1b_kinematics_and_monotonic_samples():
    # SS fields deep in hole at (-55.0, 125.0) at t=2.1s
    res = solve_fielder_throw(
        fielder_id="SS",
        intercept_x=-55.0,
        intercept_y=125.0,
        intercept_z=0.0,
        t_intercept=2.10,
        arm_strength=90.0,  # ~98.8 mph throw
        arm_accuracy=85.0,
        transfer_speed=80.0,
        body_control=80.0,
        fielding_type="GROUND_SCOOP",
        target_base="1B",
    )
    assert res.is_unassisted is False
    assert res.throw_distance_ft > 130.0
    assert res.throw_velocity_mph >= 95.0
    assert res.ball_arrival_time_s > res.throw_start_time_s
    assert len(res.samples) == 10

    # Verify strict monotonic timestamps
    timestamps = [s[3] for s in res.samples]
    for i in range(len(timestamps) - 1):
        assert timestamps[i + 1] >= timestamps[i]


def test_solve_fielder_throw_ingests_player_object_seamlessly():
    # Pass a Player object directly into solve_fielder_throw
    gun_ss = Player(
        name="Elly De La Cruz",
        position="SS",
        ratings={
            "arm_strength": 99.0,
            "arm_accuracy": 80.0,
            "transfer_speed": 85.0,
            "body_control": 90.0,
            "range": 95.0,
        },
    )
    res = solve_fielder_throw(
        fielder_id="SS",
        intercept_x=-45.0,
        intercept_y=115.0,
        intercept_z=0.0,
        t_intercept=1.50,
        fielder=gun_ss,
        fielding_type="GROUND_SCOOP",
        target_base="1B",
    )
    assert res.throw_velocity_mph == pytest.approx(70.0 + 0.99 * 32.0, abs=0.1)
    assert res.transfer_time_s < 0.55

