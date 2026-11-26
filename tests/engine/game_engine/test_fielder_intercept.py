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
    # Hard line drive: 106 mph, 17 deg launch, spray -34 (toward deep LF corner alley)
    # The ball sails over the shortstop's head at 12 ft elevation, way above SS vertical reach.
    # The LF starts at (-122, 268) and cannot get underneath the ball by landing time (~2.89s, landing at 347 ft).
    # Ball lands on grass uncaught as a clean batted ball, fielded on ground rollout or unfielded.
    motion = solve_continuous_ball_flight(106.0, 17.0, -34.0)
    defense = ActiveDefense.default()
    res = solve_defense_intercept(motion, spray_deg=-34.0, defense=defense)
    # Must NOT be caught in mid-air above reach!
    if res.fielded:
        # If fielded, it must be on the bounce/roll on the ground
        assert res.intercept_z == 0.0 or res.t_intercept >= motion["t_hang"]
        assert res.fielding_type in ("GROUND_SCOOP", "UNFIELDED")


def test_ratings_driven_gap_hit_drops_for_low_iq_outfielder():
    # Slicing line drive in right-center gap alley: 98 mph, 16 deg launch, 14 deg spray
    motion = solve_continuous_ball_flight(98.0, 16.0, 14.0)

    # 1. Elite CF/RF (IQ 99, Route 99, Range 95, Reaction 95): reads slice instantly and makes running catch
    elite_defense = ActiveDefense.default()
    for pos in ("CF", "RF"):
        elite_defense.fielders[pos].player.ratings["baseball_iq"] = 99.0
        elite_defense.fielders[pos].player.ratings["reaction"] = 95.0
        elite_defense.fielders[pos].player.ratings["route_efficiency"] = 99.0
        elite_defense.fielders[pos].player.ratings["range"] = 95.0

    res_elite = solve_defense_intercept(motion, spray_deg=14.0, defense=elite_defense)
    assert res_elite.fielded is True
    assert res_elite.fielder_id in ("CF", "RF")
    assert res_elite.fielding_type in ("RUNNING_CATCH", "SLIDING_CATCH")
    assert res_elite.intercept_z >= 1.0

    # 2. Below-average outfield (IQ 45, Reaction 45, Route 50, Range 55): hesitates on jump, ball lands on grass
    slow_defense = ActiveDefense.default()
    for pos in ("CF", "RF"):
        slow_defense.fielders[pos].player.ratings["baseball_iq"] = 45.0
        slow_defense.fielders[pos].player.ratings["reaction"] = 45.0
        slow_defense.fielders[pos].player.ratings["route_efficiency"] = 50.0
        slow_defense.fielders[pos].player.ratings["range"] = 55.0

    res_slow = solve_defense_intercept(motion, spray_deg=14.0, defense=slow_defense)
    # Ball drops untouched in the grass! Fielded on the bounce/roll
    assert res_slow.intercept_z == 0.0 or res_slow.t_intercept >= motion["t_hang"]
    assert res_slow.fielding_type in ("GROUND_SCOOP", "UNFIELDED")


def test_pitcher_mound_reach_and_middle_infield_coverage():
    # 90 mph grounder at -5 deg spray: passes 5.2 ft to the left of the rubber
    # Pitcher cannot reach it; ball rolls past mound into CF at depth (NOT vacuumed 0.5s off the rubber)
    motion_neg5 = solve_continuous_ball_flight(90.0, -2.0, -5.0)
    defense = ActiveDefense.default()
    res_neg5 = solve_defense_intercept(motion_neg5, spray_deg=-5.0, defense=defense)
    assert res_neg5.fielded is True
    assert res_neg5.fielder_id != "P"  # NOT P! Pitcher does not vacuum comebacker
    assert res_neg5.t_intercept > 1.0   # Fielded at depth, not 0.5s off the rubber

    # 90 mph grounder at -18 deg spray: passes right in front of SS (7.3 ft away)
    # SS cleanly fields it with normal athletic movement (within 10 ft)
    motion_neg18 = solve_continuous_ball_flight(90.0, -2.0, -18.0)
    res_neg18 = solve_defense_intercept(motion_neg18, spray_deg=-18.0, defense=defense)
    assert res_neg18.fielded is True
    assert res_neg18.fielder_id == "SS"
    dist_ss = ((res_neg18.intercept_x - res_neg18.fielder_start[0])**2 + (res_neg18.intercept_y - res_neg18.fielder_start[1])**2)**0.5
    assert dist_ss <= 10.0  # Normal athletic reach, not 35 ft superhuman sprint!
    assert res_neg18.s_intercept <= 165.0  # Infield pickup!

    # 90 mph grounder at -15 deg spray: 13.7 ft to the left of SS
    # SS fields with lateral diving reach (<= 16 ft)
    motion_neg15 = solve_continuous_ball_flight(90.0, -2.0, -15.0)
    res_neg15 = solve_defense_intercept(motion_neg15, spray_deg=-15.0, defense=defense)
    assert res_neg15.fielded is True
    assert res_neg15.fielder_id == "SS"
    dist_dive = ((res_neg15.intercept_x - res_neg15.fielder_start[0])**2 + (res_neg15.intercept_y - res_neg15.fielder_start[1])**2)**0.5
    assert dist_dive <= 16.0
    assert res_neg15.s_intercept <= 165.0


def test_gap_alley_flies_drop_for_hits_while_center_stays_out():
    defense = ActiveDefense.default()
    # True LCF gap alley fly (98/25/-18) and deep LF line liner (100/22/-35) drop outside LF reach
    for ev, la, spray in ((98.0, 25.0, -18.0), (100.0, 22.0, -35.0)):
        motion = solve_continuous_ball_flight(ev, la, spray)
        res = solve_defense_intercept(motion, spray_deg=spray, defense=defense)
        assert res.fielding_type in ("GROUND_SCOOP", "UNFIELDED")
        assert res.t_intercept >= motion["t_hang"]

    cf_motion = solve_continuous_ball_flight(88.0, 30.0, 0.0)
    cf_res = solve_defense_intercept(cf_motion, spray_deg=0.0, defense=defense)
    assert cf_res.fielded is True
    assert cf_res.fielder_id == "CF"
    assert cf_res.fielding_type == "ROUTINE_FLY_CATCH"


def test_hard_comebacker_outside_tightened_pitcher_reach_reaches_outfield():
    defense = ActiveDefense.default()
    motion = solve_continuous_ball_flight(92.0, 0.0, -4.3)
    res = solve_defense_intercept(motion, spray_deg=-4.3, defense=defense)
    assert res.fielder_id != "P"
    assert res.s_intercept > 165.0 or res.fielded is False


def test_fielder_reaching_fly_ball_by_landing_never_returns_ground_scoop():
    """
    Whenever a fielder reaches a fly ball (launch >= 10) at or before t_hang
    (including shoestring catches at z < 0.3 ft and retreating catches within reach),
    Section 2 must classify it as an airborne catch — never GROUND_SCOOP.
    """
    defense = ActiveDefense.default()
    airborne_catch_cases = [
        (78.0, 32.0, -4.0),   # Sec 2 z < 0.3 -> previously GROUND_SCOOP
        (70.0, 42.0, -16.0),  # Sec 2 z == 0.0 at t_hang -> previously GROUND_SCOOP
        (90.0, 26.0, -15.0),  # Sec 2 z < 0.3 at t_hang -> previously GROUND_SCOOP
        (92.0, 25.0, -15.0),  # LF reaches 53.7 <= 54.7 at t_hang -> previously blocked by margin<0.20
        (90.0, 24.0, -15.0),  # LF reaches 48.9 <= 49.5 at t_hang -> previously blocked by margin<0.20
        (72.0, 36.0, -16.0),  # High 36-deg popup in front of LF -> must not take blind slice delay
    ]
    for ev, la, sp in airborne_catch_cases:
        motion = solve_continuous_ball_flight(ev, la, sp)
        res = solve_defense_intercept(motion, spray_deg=sp, defense=defense)
        assert res.fielded is True
        assert res.t_intercept <= motion["t_hang"] + 1e-6, (
            f"ev={ev} la={la} sp={sp}: expected airborne intercept <= {motion['t_hang']:.3f}s, "
            f"got {res.t_intercept:.3f}s ({res.fielding_type})"
        )
        assert res.fielding_type in ("SLIDING_CATCH", "RUNNING_CATCH", "ROUTINE_FLY_CATCH"), (
            f"ev={ev} la={la} sp={sp}: got {res.fielding_type!r}"
        )


def test_section3_ground_retrieval_does_not_teleport_fielder_to_landing_spot():
    """
    When no fielder reaches a fly ball by t_hang, Section 3 must continue
    pursuing continuously from t_hang rather than resetting delays and adding +20 ft
    at t_hang + 0.02s. Genuine gap drops (e.g. 91/24/-12, 93.6/23.9/-11.5,
    84.1/25.5/-7.3) must not be scooped within 0.05s of landing.
    """
    defense = ActiveDefense.default()
    for ev, la, sp in ((91.0, 24.0, -12.0), (93.6, 23.9, -11.5), (84.1, 25.5, -7.3)):
        motion = solve_continuous_ball_flight(ev, la, sp)
        res = solve_defense_intercept(motion, spray_deg=sp, defense=defense)
        assert res.t_intercept > motion["t_hang"] + 0.06, (
            f"ev={ev} la={la} sp={sp}: Section 3 teleported fielder to {res.t_intercept:.3f}s "
            f"(only {res.t_intercept - motion['t_hang']:+.3f}s after t_hang={motion['t_hang']:.3f}s)"
        )
        assert res.fielding_type in ("GROUND_SCOOP", "UNFIELDED")
