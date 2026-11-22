import pytest
from backend.engine.game_engine.defense import ActiveDefense
from backend.engine.game_engine.physics.fielder_intercept import (
    solve_continuous_ball_flight,
    solve_defense_intercept,
    generate_bounded_samples,
)


def test_continuous_ball_flight_connects_air_flight_to_ground_roll():
    # 95 mph at 15 deg launch: in-air flight hits grass and continues rolling
    motion = solve_continuous_ball_flight(95.0, 15.0, 0.0)
    assert motion["t_hang"] > 0.0
    assert motion["landing_distance_ft"] > 0.0
    assert motion["total_distance_ft"] > motion["landing_distance_ft"]
    assert motion["v_impact_xy"] > 0.0
    # Position at t=0 is at home plate contact height
    pos_0 = motion["position_at_t"](0.0)
    assert pos_0 == (0.0, 3.0)  # (s, z)
    # Position at t_hang is at landing distance at ground z=0
    pos_land = motion["position_at_t"](motion["t_hang"])
    assert pos_land[0] == pytest.approx(motion["landing_distance_ft"], abs=0.5)
    assert pos_land[1] == pytest.approx(0.0, abs=0.1)


def test_routine_fly_ball_intercepted_by_cf():
    # 95 mph, 30 deg launch, 0 spray: routine fly ball to CF
    motion = solve_continuous_ball_flight(95.0, 30.0, 0.0)
    defense = ActiveDefense.default()
    res = solve_defense_intercept(motion, spray_deg=0.0, defense=defense)
    assert res.fielded is True
    assert res.fielder_id == "CF"
    assert res.fielding_type in ("ROUTINE_FLY_CATCH", "RUNNING_CATCH")
    assert res.intercept_z >= 2.5
    assert len(res.samples) == 20
    assert res.samples[-1][3] == pytest.approx(res.t_intercept, abs=0.01)


def test_line_drive_in_gap_fielded_on_ground():
    # 102 mph, 14 deg launch, -35 spray: shoots left-field gap and rolls into outfield
    motion = solve_continuous_ball_flight(102.0, 14.0, -35.0)
    defense = ActiveDefense.default()
    res = solve_defense_intercept(motion, spray_deg=-35.0, defense=defense)
    assert res.fielded is True
    assert res.fielder_id == "LF"
    assert res.fielding_type in ("GROUND_SCOOP", "SLIDING_CATCH", "RUNNING_CATCH")
    assert len(res.samples) == 20
    assert res.samples[-1][3] == pytest.approx(res.t_intercept, abs=0.01)


def test_vertical_ceiling_prevents_unphysical_sky_catches():
    # 108 mph, 28 deg launch: passes over SS at z = 35 ft. SS must not catch it.
    motion = solve_continuous_ball_flight(108.0, 28.0, -18.0)
    defense = ActiveDefense.default()
    res = solve_defense_intercept(motion, spray_deg=-18.0, defense=defense)
    if res.fielded and res.fielder_id == "SS":
        assert res.intercept_z <= 8.5
    # Catch must be at z <= 8.5 ft
    assert res.intercept_z <= 8.5


def test_unfielded_ball_at_wall_clamps_to_fence():
    # Scorcher 112 mph line drive at 12 deg into deep corner gap
    motion = solve_continuous_ball_flight(112.0, 12.0, 38.0)
    # Slow defense that cannot reach the ball
    defense = ActiveDefense.default()
    for f in defense.fielders.values():
        f.player.ratings["range"] = 10.0
        f.player.ratings["reaction"] = 10.0

    res = solve_defense_intercept(motion, spray_deg=38.0, defense=defense)
    assert res.fielded is False
    assert res.fielding_type == "UNFIELDED"
    assert len(res.samples) == 20
    assert res.samples[-1][3] == pytest.approx(res.t_intercept, abs=0.05)


def test_bounded_samples_are_strictly_monotonic():
    motion = solve_continuous_ball_flight(98.0, 22.0, 10.0)
    samples = generate_bounded_samples(motion, spray_deg=10.0, t_end=3.5, sample_count=20)
    assert len(samples) == 20
    for i in range(1, len(samples)):
        # t must be strictly increasing
        assert samples[i][3] > samples[i - 1][3]
        # x and y distance from origin must be non-decreasing
        dist_prev = samples[i - 1][0] ** 2 + samples[i - 1][1] ** 2
        dist_curr = samples[i][0] ** 2 + samples[i][1] ** 2
        assert dist_curr >= dist_prev - 1e-3

