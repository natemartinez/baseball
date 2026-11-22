"""
Continuous Flight-to-Roll Trajectory & 3D Fielder Intercept Solver.

Unifies calibrated projectile in-air flight with Dr. Alan Nathan's hop and turf
friction rolling deceleration into a continuous trajectory [x(t), y(t), z(t)],
evaluating dynamic 3D fielder pursuit and catch classification.
"""

from dataclasses import dataclass
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.engine.game_engine.defense import ActiveDefense, FielderState
from backend.engine.game_engine.physics.ball_flight import (
    CONTACT_HEIGHT_FT,
    G,
    MAX_GROUND_DISTANCE_FT,
    MPH_TO_FPS,
    _clamp,
    _drag_coefficient,
    _sample_ground_at_time,
    fence_distance_for_spray,
    ground_transit_time,
    solve_ground_motion,
)


@dataclass
class InterceptResult:
    fielded: bool
    fielder_id: Optional[str]
    fielder_name: Optional[str]
    fielding_type: str
    s_intercept: float
    t_intercept: float
    intercept_x: float
    intercept_y: float
    intercept_z: float
    fielder_start: Optional[Tuple[float, float]]
    samples: List[List[float]]


def solve_continuous_ball_flight(
    exit_velocity_mph: float,
    launch_angle_deg: float,
    spray_angle_deg: float,
    contact_height_ft: float = CONTACT_HEIGHT_FT,
) -> Dict[str, Any]:
    """
    Computes a continuous 4D ball trajectory connecting in-air flight
    to ground skip bounces and turf friction rollout.
    """
    ev = _clamp(float(exit_velocity_mph), 30.0, 125.0)
    launch = _clamp(float(launch_angle_deg), -30.0, 85.0)
    spray = _clamp(float(spray_angle_deg), -80.0, 80.0)
    contact_h = _clamp(float(contact_height_ft), 0.0, 6.0)

    theta = math.radians(launch)
    v0 = ev * MPH_TO_FPS
    v0z = v0 * math.sin(theta)
    v0xy = v0 * math.cos(theta)

    if launch < 10.0:
        ground_motion = solve_ground_motion(ev, launch, contact_h)
        t_hang = ground_motion["t_descent"]
        d_landing = ground_motion["d_descent"]
        d_total = min(MAX_GROUND_DISTANCE_FT, ground_motion["d_total"])
        t_total = ground_transit_time(ground_motion, d_total)
        v_impact_xy = ground_motion["v_roll0"]
        v_impact_z = ground_motion["hops"][0]["vz_rebound"] if ground_motion["hops"] else 0.0

        def position_at_t_ground(t: float) -> Tuple[float, float]:
            if t <= 0.0:
                return (0.0, contact_h)
            if t >= t_total:
                return (d_total, 0.0)
            s, z = _sample_ground_at_time(ground_motion, contact_h, t)
            return (min(s, d_total), max(0.0, z))

        return {
            "exit_velocity_mph": round(ev, 1),
            "launch_angle_deg": round(launch, 1),
            "spray_angle_deg": round(spray, 1),
            "contact_height_ft": contact_h,
            "t_hang": round(t_hang, 3),
            "landing_distance_ft": round(d_landing, 1),
            "total_distance_ft": round(d_total, 1),
            "v_impact_xy": round(v_impact_xy, 1),
            "v_impact_z": round(v_impact_z, 1),
            "t_total": round(t_total, 3),
            "position_at_t": position_at_t_ground,
        }

    # Airborne trajectory (launch >= 10.0)
    discriminant = v0z * v0z + 2.0 * G * contact_h
    t_vac = (v0z + math.sqrt(max(0.0, discriminant))) / G
    t_vac = max(t_vac, 0.05)

    hang_factor = (
        1.0
        - 0.008 * max(0.0, launch - 45.0)
        - 0.0002 * max(0.0, 95.0 - ev)
    )
    hang_factor = _clamp(hang_factor, 0.80, 1.05)
    t_hang = _clamp(t_vac * hang_factor, 0.05, 7.0)

    k = _drag_coefficient(launch)
    d_landing = (v0xy / k) * (1.0 - math.exp(-k * t_hang)) if v0xy > 1e-6 else 0.0

    travel = v0xy * t_hang
    c = _clamp(1.0 - d_landing / travel, 0.0, 0.95) if travel > 1e-6 else 0.0

    g_eff = 2.0 * (contact_h + v0z * t_hang) / (t_hang * t_hang)
    g_eff = _clamp(g_eff, 1.0, 250.0)

    # Impact velocity vectors at landing
    v_impact_xy = v0xy * math.exp(-k * t_hang)
    v_impact_z = -(v0z - g_eff * t_hang)

    # Ground rollout solver connected at landing point
    ground_motion = solve_ground_motion(
        exit_velocity_mph=ev,
        launch_angle_deg=launch,
        contact_height_ft=0.0,
        v_xy=v_impact_xy,
        v_z=v_impact_z,
    )
    d_ground = ground_motion["d_total"]
    fence_dist = fence_distance_for_spray(spray)
    d_total = min(fence_dist, d_landing + d_ground)
    t_ground_roll = ground_transit_time(ground_motion, d_ground)
    t_total = t_hang + t_ground_roll

    def position_at_t_air(t: float) -> Tuple[float, float]:
        if t <= 0.0:
            return (0.0, contact_h)
        if t < t_hang:
            u = t / t_hang
            s = travel * u * (1.0 - c * u)
            z = contact_h + v0z * t - 0.5 * g_eff * t * t
            return (s, max(0.0, z))
        if t == t_hang:
            return (d_landing, 0.0)
        if t >= t_total:
            return (d_total, 0.0)
        # Ground rollout phase
        dt = t - t_hang
        s_g, z_g = _sample_ground_at_time(ground_motion, 0.0, dt)
        return (min(d_total, d_landing + s_g), max(0.0, z_g))

    return {
        "exit_velocity_mph": round(ev, 1),
        "launch_angle_deg": round(launch, 1),
        "spray_angle_deg": round(spray, 1),
        "contact_height_ft": contact_h,
        "t_hang": round(t_hang, 3),
        "landing_distance_ft": round(d_landing, 1),
        "total_distance_ft": round(d_total, 1),
        "v_impact_xy": round(v_impact_xy, 1),
        "v_impact_z": round(v_impact_z, 1),
        "t_total": round(t_total, 3),
        "position_at_t": position_at_t_air,
    }


def generate_bounded_samples(
    ball_flight: Dict[str, Any],
    spray_deg: float,
    t_end: float,
    sample_count: int = 20,
) -> List[List[float]]:
    """
    Generates strictly monotonic 4D [x, y, z, t] trajectory samples bounded in [0, t_end].
    samples[0] is home plate release; samples[-1] is the exact intercept point.
    """
    phi = math.radians(spray_deg)
    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    pos_fn = ball_flight["position_at_t"]
    t_end = max(0.01, float(t_end))
    contact_h = ball_flight.get("contact_height_ft", CONTACT_HEIGHT_FT)

    samples: List[List[float]] = []
    prev_s = 0.0
    for i in range(sample_count):
        u = i / (sample_count - 1)
        t = u * t_end
        if i == 0:
            samples.append([0.0, 0.0, round(contact_h, 2), 0.0])
            prev_s = 0.0
        elif i == sample_count - 1:
            s_end, z_end = pos_fn(t_end)
            s_end = max(prev_s, s_end)
            samples.append([
                round(s_end * sin_phi, 2),
                round(s_end * cos_phi, 2),
                round(z_end, 2),
                round(t_end, 3),
            ])
        else:
            s, z = pos_fn(t)
            s = max(prev_s, s)
            prev_s = s
            samples.append([
                round(s * sin_phi, 2),
                round(s * cos_phi, 2),
                round(z, 2),
                round(t, 3),
            ])

    return samples


def solve_defense_intercept(
    ball_flight: Dict[str, Any],
    spray_deg: float,
    defense: ActiveDefense,
) -> InterceptResult:
    """
    Simulates 3D fielder pursuit along the continuous ball flight path to solve
    the earliest valid defensive intercept and classify the fielding catch type.
    """
    phi = math.radians(spray_deg)
    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    pos_fn = ball_flight["position_at_t"]
    t_total = float(ball_flight["t_total"])
    t_hang = float(ball_flight["t_hang"])
    d_landing = float(ball_flight["landing_distance_ft"])
    d_total = float(ball_flight["total_distance_ft"])
    fence_dist = fence_distance_for_spray(spray_deg)

    # Pre-calculate fielder kinematic parameters
    launch = ball_flight.get("launch_angle_deg", 15.0)
    is_ground_ball = launch < 10.0
    fielders_data = []
    for f in defense.fielders.values():
        p = f.player
        fielders_data.append({
            "pos": f.position_id,
            "name": p.name,
            "x0": f.x,
            "y0": f.y,
            "t_react": p.get_reaction_time_s(),
            "eta": p.get_route_efficiency(),
            "v_sprint": p.get_sprint_speed_fps(),
            "r_glove": p.get_glove_radius_ft(),
            "r_range": p.get_defensive_rating("range"),
        })

    # 1. Infield Ground Ball Interception
    if is_ground_ball:
        candidates = []
        for fd in fielders_data:
            pos_id = fd["pos"]
            if pos_id not in ("P", "1B", "2B", "3B", "SS"):
                continue
            s_closest = fd["x0"] * sin_phi + fd["y0"] * cos_phi
            # Pitcher follow-through recovery
            if pos_id == "P" and s_closest < 50.0:
                continue
            if s_closest < 10.0 or s_closest > d_total + 5.0 or s_closest > 165.0:
                continue
            d_perp = abs(fd["x0"] * cos_phi - fd["y0"] * sin_phi)
            if pos_id == "P":
                r_ground = 6.0 + (fd["r_range"] / 100.0) * 3.0
            elif pos_id in ("1B", "3B"):
                r_ground = 10.0 + (fd["r_range"] / 100.0) * 4.0
            else:
                r_ground = 12.0 + (fd["r_range"] / 100.0) * 4.0

            if d_perp <= r_ground:
                dist = math.hypot(fd["x0"] - s_closest * sin_phi, fd["y0"] - s_closest * cos_phi)
                candidates.append((dist, s_closest, fd, d_perp))

        if candidates:
            candidates.sort(key=lambda c: c[0])
            best_dist, s_field, winner, d_perp = candidates[0]
            # Binary search for transit time t at s_field
            lo, hi = 0.0, t_total
            for _ in range(15):
                mid = (lo + hi) / 2.0
                s_mid, _ = pos_fn(mid)
                if s_mid < s_field:
                    lo = mid
                else:
                    hi = mid
            t_field = lo
            x_field = s_field * sin_phi
            y_field = s_field * cos_phi
            is_backhand = (winner["pos"] in ("SS", "3B") and spray_deg > 0) or (winner["pos"] in ("2B", "1B") and spray_deg < 0)
            fielding_type = "BACKHAND_PICK" if (d_perp > winner["r_glove"] and is_backhand) else "GROUND_SCOOP"
            samples = generate_bounded_samples(ball_flight, spray_deg, t_field, 20)
            return InterceptResult(
                fielded=True,
                fielder_id=winner["pos"],
                fielder_name=winner["name"],
                fielding_type=fielding_type,
                s_intercept=round(s_field, 1),
                t_intercept=round(t_field, 3),
                intercept_x=round(x_field, 2),
                intercept_y=round(y_field, 2),
                intercept_z=0.0,
                fielder_start=(winner["x0"], winner["y0"]),
                samples=samples,
            )

    # 2. Airborne Flight Interception (t <= t_hang)
    dt = 0.02
    steps = int(math.ceil(t_hang / dt))
    for step in range(steps + 1):
        t = min(t_hang, step * dt)
        s, z = pos_fn(t)
        if s >= fence_dist:
            break
        z_max = 9.5 if s >= fence_dist - 5.0 else 8.5
        if z > z_max:
            continue
        x = s * sin_phi
        y = s * cos_phi
        candidates = []
        for fd in fielders_data:
            pos_id = fd["pos"]
            is_infield = pos_id in ("P", "1B", "2B", "3B", "SS")
            if is_infield and y > 185.0:
                continue
            if not is_infield and y < 125.0:
                continue
            dist = math.hypot(x - fd["x0"], y - fd["y0"])
            t_react = fd["t_react"]
            if t <= t_react:
                r_reach = fd["r_glove"]
            else:
                dt_sprint = t - t_react
                r_max = (56.0 if is_infield else 76.0) + (fd["r_range"] / 100.0) * 8.0
                r_reach = min(r_max, fd["v_sprint"] * dt_sprint * fd["eta"] * 0.85) + fd["r_glove"]
            if dist <= r_reach:
                margin = (r_reach - dist) / fd["v_sprint"] if fd["v_sprint"] > 0 else 0.0
                candidates.append((dist, margin, fd))

        if candidates:
            candidates.sort(key=lambda c: c[0])
            best_dist, best_margin, winner = candidates[0]
            if s >= fence_dist - 5.0 and z >= 7.0:
                fielding_type = "WALL_LEAP"
            elif z >= 2.5:
                fielding_type = "ROUTINE_FLY_CATCH" if best_margin >= 0.35 else "RUNNING_CATCH"
            elif 0.3 <= z < 2.5:
                fielding_type = "SLIDING_CATCH"
            else:
                fielding_type = "GROUND_SCOOP"

            samples = generate_bounded_samples(ball_flight, spray_deg, t, 20)
            return InterceptResult(
                fielded=True,
                fielder_id=winner["pos"],
                fielder_name=winner["name"],
                fielding_type=fielding_type,
                s_intercept=round(s, 1),
                t_intercept=round(t, 3),
                intercept_x=round(x, 2),
                intercept_y=round(y, 2),
                intercept_z=round(z, 2),
                fielder_start=(winner["x0"], winner["y0"]),
                samples=samples,
            )

    # 3. Ball Lands Uncaught: Outfielders Retrieve Rolling Ball
    steps_total = int(math.ceil(t_total / dt))
    for step in range(steps + 1, steps_total + 1):
        t = min(t_total, step * dt)
        s, z = pos_fn(t)
        if s >= fence_dist:
            break
        x = s * sin_phi
        y = s * cos_phi
        candidates = []
        for fd in fielders_data:
            pos_id = fd["pos"]
            if pos_id in ("P", "1B", "2B", "3B", "SS"):
                continue
            dist = math.hypot(x - fd["x0"], y - fd["y0"])
            dt_sprint = max(0.0, t - fd["t_react"])
            r_reach = fd["v_sprint"] * dt_sprint * fd["eta"] + fd["r_glove"]
            if dist <= r_reach:
                candidates.append((dist, fd))
        if candidates:
            candidates.sort(key=lambda c: c[0])
            best_dist, winner = candidates[0]
            samples = generate_bounded_samples(ball_flight, spray_deg, t, 20)
            return InterceptResult(
                fielded=True,
                fielder_id=winner["pos"],
                fielder_name=winner["name"],
                fielding_type="GROUND_SCOOP",
                s_intercept=round(s, 1),
                t_intercept=round(t, 3),
                intercept_x=round(x, 2),
                intercept_y=round(y, 2),
                intercept_z=round(z, 2),
                fielder_start=(winner["x0"], winner["y0"]),
                samples=samples,
            )

    # 4. Ball reached rest or wall unfielded
    s_end = min(d_total, fence_dist)
    samples = generate_bounded_samples(ball_flight, spray_deg, t_total, 20)
    return InterceptResult(
        fielded=False,
        fielder_id=None,
        fielder_name=None,
        fielding_type="UNFIELDED",
        s_intercept=round(s_end, 1),
        t_intercept=round(t_total, 3),
        intercept_x=round(s_end * sin_phi, 2),
        intercept_y=round(s_end * cos_phi, 2),
        intercept_z=0.0,
        fielder_start=None,
        samples=samples,
    )
