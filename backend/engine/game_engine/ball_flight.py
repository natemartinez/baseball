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
GROUND_CARRY_FACTOR = 0.65

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
        if launch < GROUND_LAUNCH_ANGLE:
            distance *= GROUND_CARRY_FACTOR
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
        samples.append([round(x, 2), round(y, 2), round(z, 2)])

    samples[0] = [0.0, 0.0, round(contact_height, 2)]
    samples[-1] = [landing_x, landing_y, 0.0]

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
