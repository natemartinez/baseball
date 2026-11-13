"""
Pitcher Arsenal Payload Serialization.

Builds standardized arsenal payloads with Statcast and display metadata
for client pitch selection chips and recommendations.
"""

from typing import Any, Dict, List, Optional

DEFAULT_ARSENAL_PAYLOAD: List[Dict[str, Any]] = [
    {
        'id': '4SFB',
        'name': '4-Seam Fastball',
        'category': 'FASTBALL',
        'velocity_mph': 97.4,
        'velocity_min_mph': 95.4,
        'velocity_max_mph': 99.4,
        'velocity_display': '95–99 mph',
        'spin_rpm': 2480,
        'break_rating': 90,
        'control_rating': 84,
        'command': 84.0,
        'max_radius_inches': 1.5,
        'sigma': 0.05,
        'tunnel_partners': ['SWP', 'KC'],
        'statcast': {
            'whiff_pct': 25.0,
            'chase_pct': 24.2,
            'gb_pct': 34.0,
            'stuff_plus': 118,
            'zone_pct': 56.0,
            'run_value': -4,
        },
    },
    {
        'id': 'SWP',
        'name': 'Spin Monster Sweeper',
        'category': 'BREAKING',
        'velocity_mph': 83.5,
        'velocity_min_mph': 81.5,
        'velocity_max_mph': 85.5,
        'velocity_display': '82–86 mph',
        'spin_rpm': 2980,
        'break_rating': 99,
        'control_rating': 80,
        'command': 80.0,
        'max_radius_inches': 1.5,
        'sigma': 0.05,
        'tunnel_partners': ['4SFB', 'SI'],
        'statcast': {
            'whiff_pct': 44.5,
            'chase_pct': 36.5,
            'gb_pct': 42.0,
            'stuff_plus': 135,
            'zone_pct': 42.0,
            'run_value': -12,
        },
    },
    {
        'id': 'SI',
        'name': 'Power Sinker',
        'category': 'FASTBALL',
        'velocity_mph': 95.8,
        'velocity_min_mph': 93.8,
        'velocity_max_mph': 97.8,
        'velocity_display': '94–98 mph',
        'spin_rpm': 2310,
        'break_rating': 88,
        'control_rating': 85,
        'command': 85.0,
        'max_radius_inches': 1.5,
        'sigma': 0.05,
        'tunnel_partners': ['SWP', 'KC'],
        'statcast': {
            'whiff_pct': 14.0,
            'chase_pct': 28.0,
            'gb_pct': 57.0,
            'stuff_plus': 112,
            'zone_pct': 58.0,
            'run_value': -7,
        },
    },
    {
        'id': 'KC',
        'name': 'Spike Curveball',
        'category': 'BREAKING',
        'velocity_mph': 81.2,
        'velocity_min_mph': 79.2,
        'velocity_max_mph': 83.2,
        'velocity_display': '79–83 mph',
        'spin_rpm': 2840,
        'break_rating': 94,
        'control_rating': 78,
        'command': 78.0,
        'max_radius_inches': 2.0,
        'sigma': 0.067,
        'tunnel_partners': ['4SFB', 'SI'],
        'statcast': {
            'whiff_pct': 38.0,
            'chase_pct': 33.0,
            'gb_pct': 48.0,
            'stuff_plus': 122,
            'zone_pct': 46.0,
            'run_value': -6,
        },
    },
]


def arsenal_key(name: str) -> str:
    """Normalizes pitch names for metadata lookup and four-seam alias matching."""
    return str(name or '').strip().lower().replace('four-seam', '4-seam')


ARSENAL_DISPLAY_METADATA = {
    arsenal_key(item['name']): item for item in DEFAULT_ARSENAL_PAYLOAD
}


def build_arsenal_payload(
    pitcher: Any, active_state: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Serializes the pitcher's hydrated arsenal for the client payload.

    The display/Statcast metadata is merged by name so client chips and
    recommendations match the pitch names the engine actually resolves.
    """
    raw = list(getattr(pitcher, 'pitch_arsenal', None) or []) if pitcher else []
    if not raw:
        return [dict(item) for item in DEFAULT_ARSENAL_PAYLOAD]

    metrics_by_name = {}
    if (
        active_state
        and hasattr(active_state, 'baseline_metrics')
        and active_state.baseline_metrics
    ):
        metrics_by_name = active_state.baseline_metrics
    else:
        try:
            from backend.engine.pitching_engine.pitcher_info import evaluate_pitch_arsenal
            metrics_by_name = evaluate_pitch_arsenal(pitcher, raw)
        except Exception:
            metrics_by_name = {}

    payload: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get('name') or item.get('pitch')
        if not name:
            continue
        display = ARSENAL_DISPLAY_METADATA.get(arsenal_key(name), {})
        velocity = float(
            item.get('velocity_mph')
            or item.get('avg_velo_mph')
            or display.get('velocity_mph', 94.0)
        )
        spin = int(
            item.get('spin_rpm')
            or item.get('avg_spin_rpm')
            or display.get('spin_rpm', 2400)
        )
        horizontal_break = item.get('horizontal_break_in')
        vertical_break = item.get('induced_vertical_break_in')

        m = metrics_by_name.get(name)
        max_radius = round(m.max_radius_inches, 3) if m else 1.5
        effectiveness = round(m.baseline_effectiveness, 1) if m else 80.0

        payload.append({
            'id': str(item.get('id') or getattr(m, 'pitch_id', '') or arsenal_key(name)),
            'name': name,
            'category': str(
                item.get('category')
                or getattr(m, 'category', 'FASTBALL')
                if m
                else 'FASTBALL'
            ),
            'velocity_mph': velocity,
            'velocity_min_mph': float(
                item.get('velocity_min_mph')
                or display.get('velocity_min_mph', velocity - 2.0)
            ),
            'velocity_max_mph': float(
                item.get('velocity_max_mph')
                or display.get('velocity_max_mph', velocity + 2.0)
            ),
            'velocity_display': str(
                item.get('velocity_display')
                or f"{round(velocity - 2.0)}–{round(velocity + 2.0)} mph"
            ),
            'spin_rpm': spin,
            'spin_rate_rpm': spin,
            'spin_axis_deg': float(
                item.get('spin_axis_deg', getattr(m, 'spin_axis_deg', 180.0) if m else 180.0)
            ),
            'command': float(
                item.get('command')
                or item.get('control_rating')
                or display.get('control_rating', 75.0)
            ),
            'control_rating': float(
                item.get('control_rating')
                or item.get('command')
                or display.get('control_rating', 75.0)
            ),
            'break_rating': float(
                item.get('break_rating') or display.get('break_rating', 80.0)
            ),
            'max_radius_inches': max_radius,
            'sigma': round(m.sigma, 4) if m else 0.05,
            'effectiveness': effectiveness,
            'horizontal_break_in': float(
                horizontal_break
                if horizontal_break is not None
                else display.get('horizontal_break_in', 0.0)
            ),
            'induced_vertical_break_in': float(
                vertical_break
                if vertical_break is not None
                else display.get('induced_vertical_break_in', 0.0)
            ),
            'tunnel_partners': list(
                item.get('tunnel_partners')
                or (getattr(m, 'tunnel_partners', []) if m else [])
            ),
            'statcast': item.get('statcast') or display.get('statcast', {}),
        })
    return payload or [dict(item) for item in DEFAULT_ARSENAL_PAYLOAD]

