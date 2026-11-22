"""
Unit tests for Batter-Runner Sprint Kinematics and Base Play Clock Resolution.
"""

import pytest
from backend.engine.models.player import Player
from backend.engine.game_engine.physics.fielder_throw import solve_fielder_throw
from backend.engine.game_engine.physics.runner_timing import (
    BasePlayResult,
    calculate_home_to_first_time,
    resolve_play_at_base,
)


def test_home_to_first_sprint_timing_scaling():
    # Elite speed (100) right-handed: ~4.00s
    t_elite_rhb = calculate_home_to_first_time(100.0, is_left_handed=False)
    assert pytest.approx(t_elite_rhb, abs=0.05) == 4.00

    # Elite speed (100) left-handed (-0.08s box advantage): ~3.92s
    t_elite_lhb = calculate_home_to_first_time(100.0, is_left_handed=True)
    assert t_elite_lhb < t_elite_rhb

    # Average speed (65): ~4.30s
    t_avg = calculate_home_to_first_time(65.0, is_left_handed=False)
    assert 4.25 <= t_avg <= 4.35

    # Slow speed (20): ~4.68s
    t_slow = calculate_home_to_first_time(20.0, is_left_handed=False)
    assert t_slow > 4.60


def test_resolve_play_at_base_out_vs_safe():
    # Ball arrives at 3.90s, Runner arrives at 4.20s -> OUT by 0.30s
    throw = solve_fielder_throw("SS", -45.0, 115.0, 0.0, 2.0, 80.0, 80.0, 75.0, 75.0)
    res_out = resolve_play_at_base(throw, runner_arrival_time_s=throw.ball_arrival_time_s + 0.30)
    assert res_out.is_out is True
    assert res_out.call == "OUT"
    assert res_out.margin_s == pytest.approx(-0.30, abs=0.01)

    # Ball arrives at 4.20s, Runner arrives at 4.05s -> SAFE by 0.15s
    res_safe = resolve_play_at_base(throw, runner_arrival_time_s=throw.ball_arrival_time_s - 0.15)
    assert res_safe.is_out is False
    assert res_safe.call == "SAFE"
    assert res_safe.margin_s == pytest.approx(0.15, abs=0.01)
    assert res_safe.is_close_play is True


def test_pitcher_comebacker_timing():
    # Pitcher fields comebacker at (0.0, 55.0) at t=0.55s
    throw = solve_fielder_throw("P", 0.0, 55.0, 1.5, 0.55, 75.0, 75.0, 75.0, 75.0)
    runner_t = calculate_home_to_first_time(60.0)
    play = resolve_play_at_base(throw, runner_t)
    assert throw.throw_distance_ft > 60.0
    assert play.is_out is True
    assert play.margin_s < -0.80  # Out by a wide margin on routine comebacker


def test_calculate_home_to_first_ingests_player_object():
    speedster = Player(
        name="Corbin Carroll",
        position="CF",
        ratings={"speed": 99.0},
        bats="L",
    )
    t_carroll = calculate_home_to_first_time(batter=speedster)
    assert t_carroll < 4.00
