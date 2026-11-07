"""
Pitch Objects and Arsenal Models for the Pitching Engine.
Defines specific traits of each pitch that will be used for tracking and animation
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


PITCH_CATEGORIES: Dict[str, str] = {
    '4-Seam Fastball': 'Fastball',
    'Four-Seam Fastball': 'Fastball',
    'Cutter': 'Fastball',
    'Sinker': 'Fastball',
    'Power Sinker': 'Fastball',
    'Slider': 'Breaking',
    'Sweeper': 'Breaking',
    'Spin Monster Sweeper': 'Breaking',
    'Curveball': 'Breaking',
    'Spike Curveball': 'Breaking',
    'Slow Curve': 'Breaking',
    'Changeup': 'OffSpeed',
    'Splitter': 'OffSpeed',
}


DEFAULT_ARSENAL: List[Dict[str, Any]] = [
    {
        'id': '4SFB',
        'name': '4-Seam Fastball',
        'pitch': '4-Seam Fastball',
        'category': 'FASTBALL',
        'velocity_mph': 97.2,
        'velocity_min_mph': 95.2,
        'velocity_max_mph': 99.2,
        'velocity_display': '95–99 mph',
        'spin_rpm': 2450,
        'spin_rate_rpm': 2450,
        'spin_axis_deg': 210.0,
        'usage_pct': 0.40,
        'break_rating': 90,
        'control_rating': 84,
        'command': 84.0,
        'max_radius_inches': 1.5,
        'sigma': 0.05,
        'horizontal_break_in': -7.5,
        'induced_vertical_break_in': 16.0,
        'tunnel_partners': ['SWP', 'KC'],
    },
    {
        'id': 'SWP',
        'name': 'Spin Monster Sweeper',
        'pitch': 'Spin Monster Sweeper',
        'category': 'BREAKING',
        'velocity_mph': 83.5,
        'velocity_min_mph': 81.5,
        'velocity_max_mph': 85.5,
        'velocity_display': '82–86 mph',
        'spin_rpm': 2980,
        'spin_rate_rpm': 2980,
        'spin_axis_deg': 85.0,
        'usage_pct': 0.30,
        'break_rating': 99,
        'control_rating': 80,
        'command': 80.0,
        'max_radius_inches': 1.5,
        'sigma': 0.05,
        'horizontal_break_in': 18.2,
        'induced_vertical_break_in': 4.5,
        'tunnel_partners': ['4SFB', 'SI'],
    },
    {
        'id': 'SI',
        'name': 'Power Sinker',
        'pitch': 'Power Sinker',
        'category': 'FASTBALL',
        'velocity_mph': 95.8,
        'velocity_min_mph': 93.8,
        'velocity_max_mph': 97.8,
        'velocity_display': '94–98 mph',
        'spin_rpm': 2310,
        'spin_rate_rpm': 2310,
        'spin_axis_deg': 235.0,
        'usage_pct': 0.20,
        'break_rating': 88,
        'control_rating': 85,
        'command': 85.0,
        'max_radius_inches': 1.5,
        'sigma': 0.05,
        'horizontal_break_in': -14.0,
        'induced_vertical_break_in': 6.0,
        'tunnel_partners': ['SWP', 'KC'],
    },
    {
        'id': 'KC',
        'name': 'Spike Curveball',
        'pitch': 'Spike Curveball',
        'category': 'BREAKING',
        'velocity_mph': 81.2,
        'velocity_min_mph': 79.2,
        'velocity_max_mph': 83.2,
        'velocity_display': '79–83 mph',
        'spin_rpm': 2840,
        'spin_rate_rpm': 2840,
        'spin_axis_deg': 30.0,
        'usage_pct': 0.10,
        'break_rating': 94,
        'control_rating': 78,
        'command': 78.0,
        'max_radius_inches': 2.0,
        'sigma': 0.067,
        'horizontal_break_in': -8.0,
        'induced_vertical_break_in': -12.0,
        'tunnel_partners': ['4SFB', 'SI'],
    },
]


# Statcast movement fallback, in inches.
# Horizontal break uses the RHP convention: positive = glove side (catcher's right).
# Induced vertical break: positive = ride, negative = drop.
DEFAULT_PITCH_MOVEMENT: List[Dict[str, Any]] = [
    {'match': 'sweeper', 'hb': 18.2, 'ivb': 4.5},
    {'match': 'gyro', 'hb': 5.5, 'ivb': -1.0},
    {'match': 'slider', 'hb': 5.5, 'ivb': -1.0},
    {'match': 'four', 'hb': -7.5, 'ivb': 16.0},
    {'match': '4-seam', 'hb': -7.5, 'ivb': 16.0},
    {'match': 'curve', 'hb': -8.0, 'ivb': -12.0},
    {'match': 'sinker', 'hb': -14.0, 'ivb': 6.0},
    {'match': 'change', 'hb': -12.0, 'ivb': 2.0},
    {'match': 'split', 'hb': -6.0, 'ivb': -2.0},
    {'match': 'cutter', 'hb': 4.0, 'ivb': 6.0},
]
DEFAULT_MOVEMENT: Dict[str, float] = {'hb': -7.5, 'ivb': 16.0}


def movement_for(pitch_name: str) -> Dict[str, float]:
    """Resolve fallback HB/IVB (inches) for a pitch name via substring matching."""
    name = (pitch_name or '').lower()
    for entry in DEFAULT_PITCH_MOVEMENT:
        if entry['match'] in name:
            return {'hb': float(entry['hb']), 'ivb': float(entry['ivb'])}
    return dict(DEFAULT_MOVEMENT)


def _pitch_lookup_key(name: str) -> str:
    """
    Normalizes a pitch name for case-insensitive lookup.

    ``4-Seam`` and ``Four-Seam`` are treated as the same pitch because the
    seeded/default arsenal and the hydrated database arsenal use both spellings.
    """
    return str(name or '').strip().lower().replace('four-seam', '4-seam')


@dataclass
class Pitch:
    """Represents a single pitch type in a pitcher's arsenal."""
    name: str
    category: str
    velocity_mph: float
    spin_rpm: int
    usage_pct: float = 0.25
    break_rating: float = 80.0
    control_rating: float = 75.0
    horizontal_break_in: float = 0.0
    induced_vertical_break_in: float = 0.0
    statcast_metrics: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pitch':
        name = data.get('pitch') or data.get('name') or '4-Seam Fastball'
        category = data.get('category') or PITCH_CATEGORIES.get(name, 'Fastball')
        velocity = float(data.get('velocity_mph') or data.get('avg_velo_mph') or 94.0)
        spin = int(data.get('spin_rpm') or data.get('avg_spin_rpm') or 2400)
        usage = float(data.get('usage_pct') or data.get('usage_pct_vs_rhb') or 0.25)
        break_r = float(data.get('break_rating', 80.0))
        ctrl_r = float(data.get('control_rating', 75.0))
        metrics = data.get('statcast', {})

        fallback = movement_for(name)
        hb = data.get('horizontal_break_in')
        if hb is None:
            hb = data.get('horizontalBreakInches')
        if hb is None:
            hb = fallback['hb']
        ivb = data.get('induced_vertical_break_in')
        if ivb is None:
            ivb = data.get('inducedVerticalBreakInches')
        if ivb is None:
            ivb = fallback['ivb']

        return cls(
            name=name,
            category=category,
            velocity_mph=velocity,
            spin_rpm=spin,
            usage_pct=usage,
            break_rating=break_r,
            control_rating=ctrl_r,
            horizontal_break_in=float(hb),
            induced_vertical_break_in=float(ivb),
            statcast_metrics=metrics
        )


class PitchArsenal:
    """Manages the collection of pitches available to a pitcher."""
    def __init__(self, raw_arsenal: Optional[List[Dict[str, Any]]] = None):
        source = raw_arsenal if (raw_arsenal and len(raw_arsenal) > 0) else DEFAULT_ARSENAL
        self.pitches: List[Pitch] = [Pitch.from_dict(p) for p in source]
        self.pitch_map: Dict[str, Pitch] = {p.name: p for p in self.pitches}

    @classmethod
    def extract_from_pitcher(cls, pitcher: Any) -> 'PitchArsenal':
        """
        Extracts normalized pitch arsenal from an authoritative Player domain object,
        with boundary conversion if an unhydrated dict is passed.
        """
        if pitcher is None:
            return cls(DEFAULT_ARSENAL)

        if isinstance(pitcher, dict):
            try:
                from backend.models.player import Player
                pitcher = Player.from_dict(pitcher)
            except ImportError:
                pass

        arsenal_data = getattr(pitcher, 'pitch_arsenal', None) if not isinstance(pitcher, dict) else pitcher.get('pitch_arsenal')
        return cls(arsenal_data)


    def get(self, name: str) -> Optional[Pitch]:
        if not name:
            return None
        exact = self.pitch_map.get(name)
        if exact is not None:
            return exact
        normalized = _pitch_lookup_key(name)
        for pitch_name, pitch in self.pitch_map.items():
            if _pitch_lookup_key(pitch_name) == normalized:
                return pitch

        # Fallback alias resolution via tiers.PITCH_TYPE_ALIASES
        try:
            from tiers import PITCH_TYPE_ALIASES
        except ImportError:
            return None

        cleaned_req = str(name).strip().upper()
        req_code = PITCH_TYPE_ALIASES.get(cleaned_req)
        if not req_code:
            return None

        # 1. Match exact pitch codes in arsenal
        for pitch_name, pitch in self.pitch_map.items():
            pitch_code = PITCH_TYPE_ALIASES.get(str(pitch_name).strip().upper())
            if pitch_code == req_code:
                return pitch

        # 2. Breaking pitch families fallback (SL <-> SWP, CB <-> KC)
        family_map = {
            'SL': {'SL', 'SWP'},
            'SWP': {'SL', 'SWP'},
            'CB': {'CB', 'KC'},
            'KC': {'CB', 'KC'},
        }
        family = family_map.get(req_code)
        if family:
            for pitch_name, pitch in self.pitch_map.items():
                pitch_code = PITCH_TYPE_ALIASES.get(str(pitch_name).strip().upper())
                if pitch_code in family:
                    return pitch

        return None

    def to_raw_list(self) -> List[Dict[str, Any]]:
        return [
            {
                'name': p.name,
                'pitch': p.name,
                'category': p.category,
                'velocity_mph': p.velocity_mph,
                'spin_rpm': p.spin_rpm,
                'usage_pct': p.usage_pct,
                'break_rating': p.break_rating,
                'control_rating': p.control_rating,
                'horizontal_break_in': p.horizontal_break_in,
                'induced_vertical_break_in': p.induced_vertical_break_in,
            }
            for p in self.pitches
        ]
