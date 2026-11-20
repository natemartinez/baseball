import math
import os
from typing import Any, Dict, Optional

G = 32.174
MPH_TO_FPS = 1.46667
CONTACT_HEIGHT_FT = 3.0
TRACE_SAMPLE_COUNT = 20
MODEL_VERSION = 'calibrated-projectile-v1'

DRAG_K_AT_45 = 0.20
DRAG_K_AT_70 = 0.12
GROUND_LAUNCH_ANGLE = 10.0

# Dr. Alan Nathan's gold-standard baseball trajectory model
AIR_DRAG_GROUND_FACTOR = 0.93
COR_VERTICAL_DIRT = 0.52
COR_HORIZONTAL_DIRT = 0.78
COR_VERTICAL_GRASS = 0.42
COR_HORIZONTAL_GRASS = 0.70
COR_VERTICAL = 0.52
COR_HORIZONTAL = 0.82
SKID_TO_ROLL_FACTOR = 0.88
TURF_FRICTION_COEFF = 0.48
HOP_CUTOFF_APEX_FT = 0.20
MAX_GROUND_DISTANCE_FT = 340.0

BALL_FLIGHT_TRACE_ENABLED = os.environ.get(
    'BALL_FLIGHT_TRACE_ENABLED', '1'
).strip().lower() not in ('0', 'false', 'off', 'no')


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _as_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _drag_coefficient(launch_angle_deg: float) -> float:
    if launch_angle_deg <= 45.0:
        return DRAG_K_AT_45
    if launch_angle_deg >= 70.0:
        return DRAG_K_AT_70
    span = 70.0 - 45.0
    t = (launch_angle_deg - 45.0) / span
    return DRAG_K_AT_45 + (DRAG_K_AT_70 - DRAG_K_AT_45) * t


def solve_ground_motion(
    exit_velocity_mph: float,
    launch_angle_deg: float,
    contact_height_ft: float = CONTACT_HEIGHT_FT,
) -> Dict[str, Any]:
    """
    Kinematic ground motion solver based on Dr. Alan Nathan's equations:
    - Phase 1: Descent to first impact with z = 0.
    - Phase 2: Multi-hop skip bounces using vertical and horizontal COR.
    - Phase 3: Coulomb turf friction rolling deceleration.
    """
    theta = math.radians(launch_angle_deg)
    v0 = exit_velocity_mph * MPH_TO_FPS
    v0z = v0 * math.sin(theta)
    v0xy = v0 * math.cos(theta) * AIR_DRAG_GROUND_FACTOR

    discriminant = v0z * v0z + 2.0 * G * contact_height_ft
    t_descent = (v0z + math.sqrt(max(0.0, discriminant))) / G
    d_descent = v0xy * t_descent
    vz_impact = -(v0z - G * t_descent)
    vxy_current = v0xy

    cor_v = COR_VERTICAL_DIRT if launch_angle_deg < 0.0 else COR_VERTICAL_GRASS
    cor_h = COR_HORIZONTAL_DIRT if launch_angle_deg < 0.0 else COR_HORIZONTAL_GRASS

    vz_current = vz_impact
    hops = []
    max_hops = 3
    while len(hops) < max_hops:
        vz_hop = vz_current * cor_v
        vxy_hop = vxy_current * cor_h
        apex_ft = (vz_hop * vz_hop) / (2.0 * G)
        if apex_ft < HOP_CUTOFF_APEX_FT:
            break
        t_hop = (2.0 * vz_hop) / G
        d_hop = vxy_hop * t_hop
        hops.append({
            'vz_rebound': vz_hop,
            'vxy_rebound': vxy_hop,
            'apex_ft': apex_ft,
            'duration_s': t_hop,
            'distance_ft': d_hop,
        })
        vz_current = vz_hop
        vxy_current = vxy_hop

    a_roll = TURF_FRICTION_COEFF * G
    v_roll0 = vxy_current * SKID_TO_ROLL_FACTOR
    t_roll = v_roll0 / a_roll if a_roll > 1e-6 else 0.0
    d_roll = (v_roll0 * v_roll0) / (2.0 * a_roll) if a_roll > 1e-6 else 0.0

    d_total = d_descent + sum(h['distance_ft'] for h in hops) + d_roll
    t_total = t_descent + sum(h['duration_s'] for h in hops) + t_roll

    return {
        'v0z': v0z,
        'v0xy': v0xy,
        't_descent': t_descent,
        'd_descent': d_descent,
        'vz_impact': vz_impact,
        'hops': hops,
        'a_roll': a_roll,
        'v_roll0': v_roll0,
        't_roll': t_roll,
        'd_roll': d_roll,
        'd_total': d_total,
        't_total': t_total,
    }


def ground_transit_time(motion: Dict[str, Any], distance_ft: float) -> float:
    """
    Computes exact kinematic time to reach target distance across the 3 phases:
    - Phase 1: Descent
    - Phase 2: Multi-hop skips
    - Phase 3: Coulomb turf friction roll
    """
    target_d = max(0.0, float(distance_ft))
    v0xy = max(1e-3, motion['v0xy'])
    t_desc = motion['t_descent']
    d_desc = motion['d_descent']

    if target_d <= d_desc:
        return _clamp(target_d / v0xy, 0.05, 12.0)

    cur_d = d_desc
    cur_t = t_desc

    for hop in motion['hops']:
        dh = hop['distance_ft']
        th = hop['duration_s']
        vh = max(1e-3, hop['vxy_rebound'])
        if target_d <= cur_d + dh:
            return _clamp(cur_t + (target_d - cur_d) / vh, 0.05, 12.0)
        cur_d += dh
        cur_t += th

    rem_d = target_d - cur_d
    v_roll0 = motion['v_roll0']
    a_roll = motion['a_roll']
    if a_roll > 1e-6 and v_roll0 > 1e-6:
        disc = max(0.0, v_roll0 * v_roll0 - 2.0 * a_roll * rem_d)
        tau = (v_roll0 - math.sqrt(disc)) / a_roll
        cur_t += tau
    return _clamp(cur_t, 0.05, 12.0)


def _sample_ground_at_time(
    motion: Dict[str, Any],
    contact_height_ft: float,
    t: float,
) -> tuple[float, float]:
    t_desc = motion['t_descent']
    v0xy = motion['v0xy']
    v0z = motion['v0z']

    if t <= t_desc:
        s = v0xy * t
        z = max(0.0, contact_height_ft + v0z * t - 0.5 * G * t * t)
        return s, z

    cur_t = t_desc
    cur_d = motion['d_descent']
    for hop in motion['hops']:
        th = hop['duration_s']
        dh = hop['distance_ft']
        vh = hop['vxy_rebound']
        vzh = hop['vz_rebound']
        if t <= cur_t + th:
            dt = t - cur_t
            s = cur_d + vh * dt
            z = max(0.0, vzh * dt - 0.5 * G * dt * dt)
            return s, z
        cur_t += th
        cur_d += dh

    dt = t - cur_t
    a_roll = motion['a_roll']
    v_roll0 = motion['v_roll0']
    s = cur_d + v_roll0 * dt - 0.5 * a_roll * dt * dt
    return s, 0.0


def _build_monotonic_ground_times(
    motion: Dict[str, Any],
    transit_time_s: float,
    sample_count: int = TRACE_SAMPLE_COUNT,
) -> list[float]:
    """
    Constructs a strictly non-decreasing sequence of sample times from t=0 to t=transit_time_s.
    Captures the initial airborne descent touchdown and first hop apex while guaranteeing
    strictly monotonic distances and smooth rolling without time or position inversions.
    """
    t_desc = motion['t_descent']
    hops = motion['hops']
    t_samples = [0.0] * sample_count

    if hops and transit_time_s > t_desc + 0.05:
        t_hop1 = hops[0]['duration_s']
        if transit_time_s >= t_desc + t_hop1 + 0.1:
            t_samples[1] = 0.5 * t_desc
            t_samples[2] = t_desc
            t_samples[3] = t_desc + 0.5 * t_hop1
            t_samples[4] = t_desc + t_hop1
            t_rem_start = t_samples[4]
            denom = max(1, sample_count - 1 - 4)
            for k in range(5, sample_count):
                t_samples[k] = t_rem_start + (k - 4) * (transit_time_s - t_rem_start) / denom
            return t_samples
        elif transit_time_s > t_desc:
            t_samples[1] = 0.5 * t_desc
            t_samples[2] = t_desc
            t_rem_start = t_desc
            denom = max(1, sample_count - 1 - 2)
            for k in range(3, sample_count):
                t_samples[k] = t_rem_start + (k - 2) * (transit_time_s - t_rem_start) / denom
            return t_samples

    dt = transit_time_s / max(1, sample_count - 1)
    for k in range(sample_count):
        t_samples[k] = k * dt
    return t_samples


def _generate_ground_samples(
    motion: Dict[str, Any],
    contact_height_ft: float,
    sin_phi: float,
    cos_phi: float,
    sample_count: int,
    distance_ft: float,
    transit_time_s: float,
) -> list:
    times = _build_monotonic_ground_times(motion, transit_time_s, sample_count)
    samples = []
    for k, t in enumerate(times):
        if k == 0:
            samples.append([0.0, 0.0, round(contact_height_ft, 2), 0.0])
        elif k == sample_count - 1:
            samples.append([
                round(distance_ft * sin_phi, 1),
                round(distance_ft * cos_phi, 1),
                0.0,
                round(transit_time_s, 3),
            ])
        else:
            s, z = _sample_ground_at_time(motion, contact_height_ft, t)
            samples.append([
                round(s * sin_phi, 2),
                round(s * cos_phi, 2),
                round(z, 2),
                round(t, 3),
            ])

    return samples


def compute_batted_ball_geometry(
    exit_velocity_mph: Any,
    launch_angle_deg: Any,
    spray_angle_deg: Any,
    contact_height_ft: float = CONTACT_HEIGHT_FT,
    sample_count: int = TRACE_SAMPLE_COUNT,
) -> Optional[Dict[str, Any]]:
    """Always computes the landing geometry, independent of trace payloads."""
    ev = _as_float(exit_velocity_mph)
    launch = _as_float(launch_angle_deg)
    spray = _as_float(spray_angle_deg)
    if ev is None or launch is None or spray is None:
        return None

    ev = _clamp(ev, 30.0, 125.0)
    launch = _clamp(launch, -30.0, 85.0)
    spray = _clamp(spray, -80.0, 80.0)
    contact_value = _as_float(contact_height_ft)
    if contact_value is None:
        contact_value = CONTACT_HEIGHT_FT
    contact_height = _clamp(contact_value, 0.0, 6.0)
    try:
        sample_count = int(sample_count)
    except (TypeError, ValueError):
        sample_count = TRACE_SAMPLE_COUNT
    sample_count = max(2, min(64, sample_count))

    theta = math.radians(launch)
    phi = math.radians(spray)
    v0 = ev * MPH_TO_FPS
    v0z = v0 * math.sin(theta)
    v0xy = v0 * math.cos(theta)

    if launch < GROUND_LAUNCH_ANGLE:
        motion = solve_ground_motion(ev, launch, contact_height)
        d_raw = motion['d_total']
        distance = min(MAX_GROUND_DISTANCE_FT, d_raw)
        t_hang = ground_transit_time(motion, distance)
        landing_x = round(distance * math.sin(phi), 1)
        landing_y = round(distance * math.cos(phi), 1)
        apex_height = contact_height
        if motion['hops']:
            apex_height = max(apex_height, max(h['apex_ft'] for h in motion['hops']))

        samples = _generate_ground_samples(
            motion=motion,
            contact_height_ft=contact_height,
            sin_phi=math.sin(phi),
            cos_phi=math.cos(phi),
            sample_count=sample_count,
            distance_ft=distance,
            transit_time_s=t_hang,
        )

        return {
            'exit_velocity_mph': round(ev, 1),
            'launch_angle_deg': round(launch, 1),
            'spray_angle_deg': round(spray, 1),
            'hang_time_s': round(t_hang, 3),
            'apex_height_ft': round(apex_height, 1),
            'distance_ft': round(distance, 1),
            'landing_x_ft': landing_x,
            'landing_y_ft': landing_y,
            'sample_count': len(samples),
            'samples': samples,
            'model_version': MODEL_VERSION,
        }

    discriminant = v0z * v0z + 2.0 * G * contact_height
    t_vac = (v0z + math.sqrt(max(0.0, discriminant))) / G
    t_vac = max(t_vac, 0.05)

    hang_factor = (
        1.0
        - 0.008 * max(0.0, launch - 45.0)
        - 0.0002 * max(0.0, 95.0 - ev)
    )
    hang_factor = _clamp(hang_factor, 0.80, 1.05)
    t_hang = _clamp(t_vac * hang_factor, 0.05, 7.0)

    if abs(v0xy) < 1e-6:
        distance = 0.0
        landing_x = 0.0
        landing_y = 0.0
        c = 0.0
    else:
        k = _drag_coefficient(launch)
        distance = (v0xy / k) * (1.0 - math.exp(-k * t_hang))
        landing_x = round(distance * math.sin(phi), 1)
        landing_y = round(distance * math.cos(phi), 1)
        travel = v0xy * t_hang
        c = _clamp(1.0 - distance / travel, 0.0, 0.95) if travel > 1e-6 else 0.0

    g_eff = 2.0 * (contact_height + v0z * t_hang) / (t_hang * t_hang)
    g_eff = _clamp(g_eff, 1.0, 250.0)

    apex_height = contact_height
    if v0z > 0.0:
        apex_height += (v0z * v0z) / (2.0 * g_eff)

    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    samples = []
    for i in range(sample_count):
        u = i / (sample_count - 1)
        t = u * t_hang
        s = v0xy * t_hang * u * (1.0 - c * u)
        x = s * sin_phi
        y = s * cos_phi
        z = contact_height + v0z * t - 0.5 * g_eff * t * t
        if z < 0.0:
            z = 0.0
        samples.append([round(x, 2), round(y, 2), round(z, 2), round(t, 3)])

    samples[0] = [0.0, 0.0, round(contact_height, 2), 0.0]
    samples[-1] = [landing_x, landing_y, 0.0, round(t_hang, 3)]

    return {
        'exit_velocity_mph': round(ev, 1),
        'launch_angle_deg': round(launch, 1),
        'spray_angle_deg': round(spray, 1),
        'hang_time_s': round(t_hang, 3),
        'apex_height_ft': round(apex_height, 1),
        'distance_ft': round(distance, 1),
        'landing_x_ft': landing_x,
        'landing_y_ft': landing_y,
        'sample_count': sample_count,
        'samples': samples,
        'model_version': MODEL_VERSION,
    }


def compute_batted_ball_trace(
    exit_velocity_mph: Any,
    launch_angle_deg: Any,
    spray_angle_deg: Any,
    contact_height_ft: float = CONTACT_HEIGHT_FT,
    sample_count: int = TRACE_SAMPLE_COUNT,
) -> Optional[Dict[str, Any]]:
    """API-facing trace payload; respects the trace-telemetry flag."""
    if not BALL_FLIGHT_TRACE_ENABLED:
        return None
    return compute_batted_ball_geometry(
        exit_velocity_mph,
        launch_angle_deg,
        spray_angle_deg,
        contact_height_ft,
        sample_count,
    )
