"""
Pitch Objects and Arsenal Models for the Pitching Engine.
Defines pitch domain structures, categories, and arsenal normalization.
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
    {'name': '4-Seam Fastball', 'pitch': '4-Seam Fastball', 'velocity_mph': 97.2, 'spin_rpm': 2450, 'usage_pct': 0.40, 'break_rating': 90, 'control_rating': 84},
    {'name': 'Spin Monster Sweeper', 'pitch': 'Spin Monster Sweeper', 'velocity_mph': 83.5, 'spin_rpm': 2980, 'usage_pct': 0.30, 'break_rating': 99, 'control_rating': 80},
    {'name': 'Power Sinker', 'pitch': 'Power Sinker', 'velocity_mph': 95.8, 'spin_rpm': 2310, 'usage_pct': 0.20, 'break_rating': 88, 'control_rating': 85},
    {'name': 'Spike Curveball', 'pitch': 'Spike Curveball', 'velocity_mph': 81.2, 'spin_rpm': 2840, 'usage_pct': 0.10, 'break_rating': 94, 'control_rating': 78},
]


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
        return cls(
            name=name,
            category=category,
            velocity_mph=velocity,
            spin_rpm=spin,
            usage_pct=usage,
            break_rating=break_r,
            control_rating=ctrl_r,
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
        return self.pitch_map.get(name)

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
            }
            for p in self.pitches
        ]
