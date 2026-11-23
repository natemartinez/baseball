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


def test_routine_fly_ball_caught_at_chest_height():
    # 92 mph, 32 deg launch, 0 spray to CF (hang time ~4.6s)
    # CF arrives well in advance (~2.5s) and camps under it.
    motion = solve_continuous_ball_flight(92.0, 32.0, 0.0)
    defense = ActiveDefense.default()
    res = solve_defense_intercept(motion, spray_deg=0.0, defense=defense)
    assert res.fielded is True
    assert res.fielder_id == "CF"
    assert res.fielding_type == "ROUTINE_FLY_CATCH"
    # Must be caught at standing eye/chest level, NOT near the floor
    assert 4.5 <= res.intercept_z <= 5.5
    assert res.samples[-1][2] == pytest.approx(res.intercept_z, abs=0.1)


def test_ball_sailing_overhead_out_of_glove_range_becomes_uncaught_batted_ball():
    # Hard line drive: 106 mph, 17 deg launch, spray -30 (toward LF/CF alley)
    # The ball sails over the shortstop's head at 12 ft elevation, way above SS vertical reach.
    # The LF starts at (-115, 255) and cannot get underneath the ball by landing time (~3.6s, landing at 340 ft).
    # Ball lands on grass uncaught as a clean batted ball, fielded on ground rollout or unfielded.
    motion = solve_continuous_ball_flight(106.0, 17.0, -30.0)
    defense = ActiveDefense.default()
    res = solve_defense_intercept(motion, spray_deg=-30.0, defense=defense)
    # Must NOT be caught in mid-air above reach!
    if res.fielded:
        # If fielded, it must be on the bounce/roll on the ground
        assert res.intercept_z == 0.0 or res.t_intercept >= motion["t_hang"]
        assert res.fielding_type in ("GROUND_SCOOP", "UNFIELDED")

