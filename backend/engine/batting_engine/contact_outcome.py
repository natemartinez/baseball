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

from ..game_engine.ball_flight import compute_batted_ball_geometry, compute_batted_ball_trace


PARK_FENCE_CENTER_FT = 400.0
PARK_FENCE_LINE_FT = 330.0
FOUL_LINE_DEG = 45.0

# Standard defensive positions plus a baseline reach radius. The radius is the
# total ground a fielder can cover to make a play, not just arm's length, so it
# is intentionally larger than the fielder model. Values are in feet and are
# mirrored in frontend/app/src/services/fielders.ts.
FIELDERS: Tuple[Dict[str, Any], ...] = (
    {'id': 'P', 'label': 'P', 'name': 'pitcher', 'x': 0.0, 'y': 60.5, 'radius': 34.0},
    {'id': '1B', 'label': '1B', 'name': 'first base', 'x': 63.6, 'y': 63.6, 'radius': 56.0},
    {'id': '2B', 'label': '2B', 'name': 'second base', 'x': 45.0, 'y': 115.0, 'radius': 60.0},
    {'id': 'SS', 'label': 'SS', 'name': 'shortstop', 'x': -45.0, 'y': 115.0, 'radius': 60.0},
    {'id': '3B', 'label': '3B', 'name': 'third base', 'x': -63.6, 'y': 63.6, 'radius': 56.0},
    {'id': 'LF', 'label': 'LF', 'name': 'left field', 'x': -115.0, 'y': 255.0, 'radius': 73.0},
    {'id': 'CF', 'label': 'CF', 'name': 'center field', 'x': 0.0, 'y': 330.0, 'radius': 80.0},
    {'id': 'RF', 'label': 'RF', 'name': 'right field', 'x': 115.0, 'y': 255.0, 'radius': 73.0},
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
    Fair contact always carries the trace; fouls intentionally do not.
    """
    ev = _finite(exit_velocity_mph)
    launch = _finite(launch_angle_deg)
    spray = _finite(spray_angle_deg)
    if ev is None or launch is None or spray is None:
        return None

    ev = _clamp(ev, 45.0, 122.0)
    launch = _clamp(launch, -25.0, 78.0)
    spray = _clamp(spray, -65.0, 65.0)
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
            'batted_ball': None,
            'exit_velocity_mph': round(ev, 1),
            'launch_angle_deg': round(launch, 1),
            'spray_angle_deg': round(spray, 1),
            'fielder_name': None,
            'fielder_distance_ft': None,
            'fielder_radius_ft': None,
        }

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
        # Every fair ball outside all fielder radii is a hit. Weak grounders
        # and bloopers become infield/bloop singles instead of plate-area outs.
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
