"""
Contact-driven batted-ball outcome classification.

Rapier reports where and how the bat met the ball. This module turns the
resulting exit velocity, launch angle, and spray angle into the same
PitchResultType taxonomy used by the legacy ratings path, but it derives the
result from the actual landing point instead of ratings-based probabilities.

In-play outs come from a fielder-reach model: each fielder has a baseline
range radius around a standard position. A fair ball that lands inside any
fielder's radius is an out; a fair ball outside every radius is a hit. Both
the AI ContactResolver path and the player-contact path use this classifier.

Fielders are in Statcast feet: +X is the right-field/first-base side, +Y is
depth toward center field. The catcher is intentionally excluded so weak
grounders in front of the plate are infield hits rather than automatic outs.
"""

import math
from typing import Any, Dict, Optional, Tuple

from ..game_engine.ball_flight import (
    compute_batted_ball_geometry,
    compute_batted_ball_trace,
    ground_transit_time,
    solve_ground_motion,
)


PARK_FENCE_CENTER_FT = 400.0
PARK_FENCE_LINE_FT = 330.0
FOUL_LINE_DEG = 45.0

# Standard defensive positions plus a baseline reach radius. The radius is the
# total ground a fielder can cover to make a play, not just arm's length, so it
# is intentionally larger than the fielder model. Values are in feet and are
# mirrored in frontend/app/src/services/fielders.ts.
FIELDERS: Tuple[Dict[str, Any], ...] = (
    {'id': 'P', 'label': 'P', 'name': 'pitcher', 'x': 0.0, 'y': 60.5, 'radius': 34.0, 'ground_radius': 8.0, 'is_infield': True},
    {'id': '1B', 'label': '1B', 'name': 'first base', 'x': 63.6, 'y': 63.6, 'radius': 56.0, 'ground_radius': 13.0, 'is_infield': True},
    {'id': '2B', 'label': '2B', 'name': 'second base', 'x': 45.0, 'y': 115.0, 'radius': 60.0, 'ground_radius': 15.0, 'is_infield': True},
    {'id': 'SS', 'label': 'SS', 'name': 'shortstop', 'x': -45.0, 'y': 115.0, 'radius': 60.0, 'ground_radius': 15.0, 'is_infield': True},
    {'id': '3B', 'label': '3B', 'name': 'third base', 'x': -63.6, 'y': 63.6, 'radius': 56.0, 'ground_radius': 13.0, 'is_infield': True},
    {'id': 'LF', 'label': 'LF', 'name': 'left field', 'x': -115.0, 'y': 255.0, 'radius': 73.0, 'ground_radius': 0.0, 'is_infield': False},
    {'id': 'CF', 'label': 'CF', 'name': 'center field', 'x': 0.0, 'y': 330.0, 'radius': 80.0, 'ground_radius': 0.0, 'is_infield': False},
    {'id': 'RF', 'label': 'RF', 'name': 'right field', 'x': 115.0, 'y': 255.0, 'radius': 73.0, 'ground_radius': 0.0, 'is_infield': False},
)


def _finite(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _fence_distance(spray_angle_deg: float) -> float:
    fraction = min(abs(spray_angle_deg), FOUL_LINE_DEG) / FOUL_LINE_DEG
    return PARK_FENCE_CENTER_FT - (PARK_FENCE_CENTER_FT - PARK_FENCE_LINE_FT) * fraction


def _contact_quality(exit_velocity: float, launch_angle: float) -> str:
    if exit_velocity >= 98.0 and 12.0 <= launch_angle <= 34.0:
        return 'BARREL'
    if exit_velocity >= 88.0:
        return 'SOLID'
    return 'WEAK'


def _field_name(spray_angle: float) -> str:
    if spray_angle >= 22.0:
        return 'right field'
    if spray_angle <= -22.0:
        return 'left field'
    return 'center field'


def fielder_for_landing(
    landing_x_ft: float,
    landing_y_ft: float,
) -> Optional[Dict[str, Any]]:
    """Returns the nearest fielder whose reach radius contains the landing."""
    nearest: Optional[Dict[str, Any]] = None
    for fielder in FIELDERS:
        distance = math.hypot(landing_x_ft - fielder['x'], landing_y_ft - fielder['y'])
        if distance <= fielder['radius'] and (nearest is None or distance < nearest['distance']):
            nearest = {**fielder, 'distance': distance}
    return nearest


def fielder_for_ground_path(
    spray_deg: float,
    total_distance: float,
) -> Optional[Dict[str, Any]]:
    """Returns the infielder who intercepts the ground ball along its trajectory."""
    phi = math.radians(spray_deg)
    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    candidate: Optional[Dict[str, Any]] = None

    for f in FIELDERS:
        if not f.get('is_infield', False):
            continue
        s_closest = f['x'] * sin_phi + f['y'] * cos_phi
        if s_closest < 10.0 or s_closest > total_distance + 5.0:
            continue
        d_perp = abs(f['x'] * cos_phi - f['y'] * sin_phi)
        ground_radius = f.get('ground_radius', f['radius'])
        if d_perp <= ground_radius:
            dist = math.hypot(f['x'] - s_closest * sin_phi, f['y'] - s_closest * cos_phi)
            if candidate is None or dist < candidate['distance']:
                candidate = {**f, 'distance': dist, 's_fielded': s_closest}

    return candidate


def _clamp_samples_to_distance(
    samples: list,
    target_dist: float,
    sin_phi: float,
    cos_phi: float,
    target_count: int = 20,
) -> list:
    out = []
    for pt in samples:
        s = math.hypot(pt[0], pt[1])
        if s < target_dist:
            out.append(pt)
        else:
            break
    end_pt = [round(target_dist * sin_phi, 1), round(target_dist * cos_phi, 1), 0.0]
    out.append(end_pt)
    if len(out) < 2 or target_count <= 2:
        return out

    cum_lens = [0.0]
    for i in range(1, len(out)):
        dx = out[i][0] - out[i - 1][0]
        dy = out[i][1] - out[i - 1][1]
        dz = out[i][2] - out[i - 1][2]
        cum_lens.append(cum_lens[-1] + math.sqrt(dx * dx + dy * dy + dz * dz))

    total_len = cum_lens[-1]
    if total_len < 1e-6:
        return [out[0]] * target_count

    resampled = [out[0]]
    cur_idx = 0
    for j in range(1, target_count - 1):
        target_s = j * total_len / (target_count - 1)
        while cur_idx < len(cum_lens) - 2 and cum_lens[cur_idx + 1] < target_s:
            cur_idx += 1
        seg_len = cum_lens[cur_idx + 1] - cum_lens[cur_idx]
        alpha = (target_s - cum_lens[cur_idx]) / seg_len if seg_len > 1e-6 else 0.0
        p0 = out[cur_idx]
        p1 = out[cur_idx + 1]
        resampled.append([
            round(p0[0] + alpha * (p1[0] - p0[0]), 2),
            round(p0[1] + alpha * (p1[1] - p0[1]), 2),
            round(max(0.0, p0[2] + alpha * (p1[2] - p0[2])), 2),
        ])
    resampled.append(end_pt)
    return resampled


def _describe(
    call: str,
    exit_velocity: float,
    launch_angle: float,
    spray_angle: float,
    distance: float,
    fielder: Optional[Dict[str, Any]] = None,
) -> str:
    field = _field_name(spray_angle)
    if call == 'HOME_RUN':
        return f'CRUSHED! Home run to {field} ({exit_velocity} MPH, {launch_angle}°).'
    if call == 'TRIPLE':
        return f'Triple into the gap at {field} ({exit_velocity} MPH, {launch_angle}°).'
    if call == 'DOUBLE':
        return f'Double into the gap at {field} ({exit_velocity} MPH, {launch_angle}°).'
    if call == 'SINGLE':
        if distance < 90.0:
            return f'Infield single ({exit_velocity} MPH, {launch_angle}°).'
        return f'Base hit into {field} ({exit_velocity} MPH, {launch_angle}°).'
    if call == 'FOUL':
        return f'Foul ball into {field} ({exit_velocity} MPH, {launch_angle}°).'
    if call == 'IN_PLAY_OUT' and fielder is not None:
        label = fielder['label']
        if launch_angle < 8.0:
            return f'Ground out to {label} ({exit_velocity} MPH, {launch_angle}°).'
        if launch_angle > 38.0:
            return f'Pop out to {label} ({exit_velocity} MPH, {launch_angle}°).'
        return f'Fly out to {label} ({exit_velocity} MPH, {launch_angle}°).'
    return f'Out in {field} ({exit_velocity} MPH, {launch_angle}°).'


def resolve_contact_outcome(
    exit_velocity_mph: Any,
    launch_angle_deg: Any,
    spray_angle_deg: Any,
    batter_speed: float = 75.0,
) -> Optional[Dict[str, Any]]:
    """
    Classify a player-contact batted ball from its actual landing point.

    Returns ``None`` when the inputs are invalid or the trace flag is disabled.
    All batted contact (fair or foul) carries the trace for flight animation and tracking.
    """
    ev = _finite(exit_velocity_mph)
    launch = _finite(launch_angle_deg)
    spray = _finite(spray_angle_deg)
    if ev is None or launch is None or spray is None:
        return None

    ev = _clamp(ev, 45.0, 122.0)
    launch = _clamp(launch, -25.0, 78.0)
    spray = _clamp(spray, -75.0, 75.0)
    speed = _clamp(_finite(batter_speed) or 75.0, 0.0, 100.0)

    geometry = compute_batted_ball_geometry(ev, launch, spray)
    if geometry is None:
        return None
    trace = compute_batted_ball_trace(ev, launch, spray)

    landing_x = float(geometry['landing_x_ft'])
    landing_y = float(geometry['landing_y_ft'])
    distance = float(geometry['distance_ft'])
    fair = landing_y > 0.0 and abs(landing_x) <= landing_y

    if not fair:
        return {
            'call': 'FOUL',
            'is_in_play': False,
            'description': _describe('FOUL', ev, launch, spray, distance),
            'contact_quality': _contact_quality(ev, launch),
            'batted_ball': trace,
            'exit_velocity_mph': round(ev, 1),
            'launch_angle_deg': round(launch, 1),
            'spray_angle_deg': round(spray, 1),
            'fielder_name': None,
            'fielder_distance_ft': None,
            'fielder_radius_ft': None,
        }

    if launch < 10.0:
        ground_fielder = fielder_for_ground_path(spray, distance)
        if ground_fielder is not None:
            call = 'IN_PLAY_OUT'
            fielder = ground_fielder
            s_field = ground_fielder['s_fielded']
            landing_x = round(s_field * math.sin(math.radians(spray)), 1)
            landing_y = round(s_field * math.cos(math.radians(spray)), 1)
            distance = round(s_field, 1)
            if trace is not None:
                motion = solve_ground_motion(ev, launch)
                trace['hang_time_s'] = round(ground_transit_time(motion, distance), 3)
                trace['landing_x_ft'] = landing_x
                trace['landing_y_ft'] = landing_y
                trace['distance_ft'] = distance
                target_count = len(trace.get('samples', [])) or 20
                trace['samples'] = _clamp_samples_to_distance(
                    trace['samples'],
                    distance,
                    math.sin(math.radians(spray)),
                    math.cos(math.radians(spray)),
                    target_count=target_count,
                )
                trace['sample_count'] = len(trace['samples'])
        else:
            if distance >= 250.0 and abs(spray) >= 25.0 and speed >= 78.0:
                call = 'DOUBLE'
            else:
                call = 'SINGLE'
            fielder = None
    else:
        fielder = fielder_for_landing(landing_x, landing_y)
        fence = _fence_distance(spray)

        if distance >= fence + 3.0:
            call = 'HOME_RUN'
            fielder = None
        elif fielder is not None:
            call = 'IN_PLAY_OUT'
        elif distance >= 320.0 and abs(spray) >= 25.0 and speed >= 78.0:
            call = 'TRIPLE'
        elif distance >= 300.0 or (distance >= 250.0 and 8.0 <= launch <= 32.0):
            call = 'DOUBLE'
        else:
            call = 'SINGLE'

    return {
        'call': call,
        'is_in_play': True,
        'description': _describe(call, ev, launch, spray, distance, fielder),
        'contact_quality': _contact_quality(ev, launch),
        'batted_ball': trace,
        'exit_velocity_mph': round(ev, 1),
        'launch_angle_deg': round(launch, 1),
        'spray_angle_deg': round(spray, 1),
        'fielder_name': fielder['label'] if fielder is not None else None,
        'fielder_distance_ft': round(fielder['distance'], 1) if fielder is not None else None,
        'fielder_radius_ft': fielder['radius'] if fielder is not None else None,
    }
