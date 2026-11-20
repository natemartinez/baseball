import math
import pytest
from backend.engine.game_engine.ball_flight import (
    compute_batted_ball_geometry,
    compute_batted_ball_trace,
    solve_ground_motion,
    AIR_DRAG_GROUND_FACTOR,
    COR_VERTICAL_DIRT,
    COR_HORIZONTAL_DIRT,
    COR_VERTICAL_GRASS,
    COR_HORIZONTAL_GRASS,
    SKID_TO_ROLL_FACTOR,
    TURF_FRICTION_COEFF,
    MAX_GROUND_DISTANCE_FT,
)


def test_recalibrated_ground_physics_parameters():
    assert AIR_DRAG_GROUND_FACTOR == 0.93
    assert COR_VERTICAL_DIRT == 0.52
    assert COR_HORIZONTAL_DIRT == 0.78
    assert COR_VERTICAL_GRASS == 0.42
    assert COR_HORIZONTAL_GRASS == 0.70
    assert SKID_TO_ROLL_FACTOR == 0.88
    assert TURF_FRICTION_COEFF == 0.48
    assert MAX_GROUND_DISTANCE_FT == 340.0


def test_samples_emit_monotonic_4d_timestamps():
    # Test downward chopper (LA < 0)
    res_chopper = compute_batted_ball_geometry(88.0, -5.0, -21.4)
    samples_c = res_chopper['samples']
    assert len(samples_c) == 20
    assert len(samples_c[0]) == 4
    assert samples_c[0] == [0.0, 0.0, 3.0, 0.0]
    assert samples_c[-1][3] == res_chopper['hang_time_s']
    for i in range(1, len(samples_c)):
        assert samples_c[i][3] >= samples_c[i - 1][3]

    # Test airborne hit (LA >= 10)
    res_fly = compute_batted_ball_geometry(90.0, 32.0, 24.0)
    samples_f = res_fly['samples']
    assert len(samples_f) == 20
    assert len(samples_f[0]) == 4
    assert samples_f[0] == [0.0, 0.0, 3.0, 0.0]
    assert samples_f[-1][3] == res_fly['hang_time_s']
    for i in range(1, len(samples_f)):
        assert samples_f[i][3] >= samples_f[i - 1][3]



def test_exact_phase1_airborne_descent_calculations():
    # 90.0 MPH (132.0003 ft/s) at 0 deg launch from 3.0 ft contact height
    # Under AIR_DRAG_GROUND_FACTOR = 0.93:
    # v0xy = 132.0003 * 0.93 = 122.76 ft/s
    # t0 = sqrt(2 * h / g) = sqrt(6.0 / 32.174) = 0.4318 s
    # d0 = v0xy * t0 = 122.76 * 0.4318 = 53.01 ft
    # vz_impact = g * t0 = 32.174 * 0.4318 = 13.89 ft/s
    motion = solve_ground_motion(exit_velocity_mph=90.0, launch_angle_deg=0.0)
    assert motion['t_descent'] == pytest.approx(0.4318, rel=1e-2)
    assert motion['d_descent'] == pytest.approx(53.01, rel=1e-2)
    assert motion['vz_impact'] == pytest.approx(13.89, rel=1e-2)


def test_exact_phase2_multi_hop_skip_calculations():
    # For LA >= 0, COR_VERTICAL_GRASS = 0.42, COR_HORIZONTAL_GRASS = 0.70
    # Hop 1:
    # vz1 = 13.89 * 0.42 = 5.83 ft/s
    # apex1 = vz1^2 / (2 * g) = 5.83^2 / 64.348 = 0.53 ft
    # t_hop1 = 2 * vz1 / g = 2 * 5.83 / 32.174 = 0.363 s
    # vxy1 = 122.76 * 0.70 = 85.93 ft/s
    # d_hop1 = vxy1 * t_hop1 = 85.93 * 0.363 = 31.17 ft
    #
    # Hop 2:
    # vz2 = 5.83 * 0.42 = 2.45 ft/s
    # apex2 = 2.45^2 / 64.348 = 0.093 ft < 0.20 ft (CUTOFF REACHED)
    motion = solve_ground_motion(exit_velocity_mph=90.0, launch_angle_deg=0.0)
    hops = motion['hops']
    assert len(hops) == 1, f"Expected exactly 1 hop before cutoff, got {len(hops)}"
    assert hops[0]['apex_ft'] == pytest.approx(0.53, rel=0.05)
    assert hops[0]['distance_ft'] == pytest.approx(31.17, rel=0.05)


def test_exact_phase3_turf_roll_calculations():
    # a_roll = mu * g = 0.48 * 32.174 = 15.44 ft/s^2
    # v_roll0 = vxy1 * SKID_TO_ROLL_FACTOR = 85.93 * 0.88 = 75.62 ft/s
    # t_roll = v_roll0 / a_roll = 75.62 / 15.44 = 4.90 s
    # d_roll = v_roll0^2 / (2 * a_roll) = 75.62^2 / 30.89 = 185.14 ft
    motion = solve_ground_motion(exit_velocity_mph=90.0, launch_angle_deg=0.0)
    assert motion['a_roll'] == pytest.approx(15.44, rel=1e-2)
    assert motion['v_roll0'] == pytest.approx(75.62, rel=0.05)
    assert motion['d_roll'] == pytest.approx(185.14, rel=0.05)


def test_ground_ball_trajectory_samples_structure():
    trace = compute_batted_ball_trace(90.0, 0.0, 0.0)
    assert trace is not None
    samples = trace['samples']
    assert len(samples) == 20
    # Point 0 is contact height with t=0
    assert samples[0] == [0.0, 0.0, 3.0, 0.0]
    # Check that samples feature at least one point where z drops to ~0 then bounces back up
    z_vals = [s[2] for s in samples]
    first_drop_idx = next(i for i, z in enumerate(z_vals) if z <= 0.1 and i > 0)
    assert max(z_vals[first_drop_idx:]) >= 0.2
    # Final points are pure ground roll (z == 0.0) with timestamp == hang_time_s
    assert samples[-1][2] == 0.0
    assert samples[-1][3] == pytest.approx(trace['hang_time_s'], abs=0.01)


def test_ground_kinematic_transit_time_is_realistic():
    from backend.engine.game_engine.ball_flight import (
        solve_ground_motion,
        ground_transit_time,
    )
    motion = solve_ground_motion(90.0, 0.0)
    assert 0.35 <= ground_transit_time(motion, 60.0) <= 0.60
    assert 1.10 <= ground_transit_time(motion, 120.0) <= 1.45
    assert 2.30 <= ground_transit_time(motion, 200.0) <= 2.90


def test_ground_ball_samples_are_strictly_monotonic_across_all_archetypes():
    """
    Prevents jagged skips and backward distance snaps when grounders cross
    from the infield (100-140 ft) to outfield (>180 ft).
    """
    for ev in [70.0, 80.0, 88.0, 92.0, 95.0, 105.0]:
        for la in [-10.0, 0.0, 2.0, 4.0, 8.0]:
            for spray in [-25.0, 0.0, 18.0]:
                trace = compute_batted_ball_trace(ev, la, spray)
                assert trace is not None
                samples = trace['samples']
                assert len(samples) == 20
                prev_dist = -1e-6
                for i, pt in enumerate(samples):
                    dist = math.hypot(pt[0], pt[1])
                    assert dist >= prev_dist - 1e-4, (
                        f"Non-monotonic distance at EV={ev}, LA={la}, spray={spray}, "
                        f"sample {i}: {dist:.2f}ft < prev {prev_dist:.2f}ft"
                    )
                    prev_dist = dist

