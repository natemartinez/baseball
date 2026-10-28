"""
In-Game Batter State & Rating Normalization.

Hydrates batter ratings, handedness, and hot/cold zone slugging from the
authoritative Player model without mutating persistent records. All missing
values fall back to neutral league defaults rather than a specific player's
profile.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

LEAGUE_AVG_SLG = 0.400

# Neutral 13-zone slugging profile. These are intentionally generic; a
# batter's stored zones override them when present.
DEFAULT_BATTER_ZONES: Dict[str, float] = {
    'upper-in': 0.400,
    'upper-middle': 0.410,
    'upper-away': 0.380,
    'middle-in': 0.430,
    'heart': 0.470,
    'middle-away': 0.380,
    'lower-in': 0.400,
    'lower-middle': 0.390,
    'lower-away': 0.350,
    'chase-high': 0.280,
    'chase-low': 0.260,
    'chase-in': 0.290,
    'chase-away': 0.270,
}

DEFAULT_BATTER_RATINGS: Dict[str, float] = {
    'power': 60.0,
    'contact': 60.0,
    'vision': 60.0,
    'speed': 50.0,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _raw_batter_value(batter: Any, key: str, default: float) -> float:
    """Reads a value from a Player, a dict payload, or a ratings map."""
    if batter is None:
        return default

    if isinstance(batter, dict):
        direct = batter.get(key)
        if direct is not None:
            return float(direct)
        ratings = batter.get('ratings') or {}
        if isinstance(ratings, dict):
            for rating_key, value in ratings.items():
                if str(rating_key).lower() == key.lower():
                    return float(value)
        return default

    getter = getattr(batter, 'get_rating', None)
    if callable(getter):
        return float(getter(key, default))

    ratings = getattr(batter, 'ratings', None)
    if isinstance(ratings, dict):
        for rating_key, value in ratings.items():
            if str(rating_key).lower() == key.lower():
                return float(value)

    value = getattr(batter, key, None)
    return float(value) if value is not None else default


def get_batter_hand(batter: Any) -> str:
    """Returns the batter's side ('L' or 'R'), defaulting to right-handed."""
    if batter is None:
        return 'R'

    if isinstance(batter, dict):
        raw = (
            batter.get('handedness')
            or batter.get('bats')
            or (batter.get('vitals') or {}).get('bats')
        )
    else:
        raw = getattr(batter, 'handedness', None)
        vitals = getattr(batter, 'vitals', None)
        if not raw and isinstance(vitals, dict):
            raw = vitals.get('bats') or vitals.get('handedness')

    text = str(raw or 'R').upper()
    if text.startswith('L'):
        return 'L'
    return 'R'


def get_effective_batter_side(batter: Any, pitcher_hand: str = 'R') -> str:
    """Resolves switch-hitters to the side opposite the pitcher."""
    if batter is None:
        return 'R'

    raw = None
    if isinstance(batter, dict):
        raw = (
            batter.get('handedness')
            or batter.get('bats')
            or (batter.get('vitals') or {}).get('bats')
        )
    else:
        raw = getattr(batter, 'handedness', None)
        vitals = getattr(batter, 'vitals', None)
        if not raw and isinstance(vitals, dict):
            raw = vitals.get('bats') or vitals.get('handedness')

    text = str(raw or 'R').upper()
    if text.startswith('S'):
        return 'L' if str(pitcher_hand).upper().startswith('R') else 'R'
    if text.startswith('L'):
        return 'L'
    return 'R'


def normalize_hot_zones(raw_zones: Any) -> Dict[str, float]:
    """
    Normalizes a batter's zone data into a complete 13-zone slugging map.

    Accepts:
      - a {zone_name: slugging} dict
      - a list of {zone|name, slugging|slg|slg_multiplier|multiplier} dicts
    """
    zones = dict(DEFAULT_BATTER_ZONES)
    if not raw_zones:
        return zones

    if isinstance(raw_zones, dict):
        for zone_name, raw_value in raw_zones.items():
            name = str(zone_name).lower().strip()
            if name not in DEFAULT_BATTER_ZONES:
                continue
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            # A stored slugging value is normally < 1.0; larger values are
            # treated as multipliers for compatibility with legacy payloads.
            if value > 1.0:
                value = LEAGUE_AVG_SLG * value
            zones[name] = round(_clamp(value, 0.050, 1.200), 3)
        return zones

    if isinstance(raw_zones, list):
        for item in raw_zones:
            if not isinstance(item, dict):
                continue
            raw_name = item.get('zone')
            if not isinstance(raw_name, str):
                raw_name = item.get('name')
            name = str(raw_name or '').lower().strip()
            if name not in DEFAULT_BATTER_ZONES:
                continue

            value = item.get('slugging', item.get('slg'))
            if value is None:
                multiplier = item.get('slg_multiplier', item.get('multiplier'))
                if multiplier is not None:
                    try:
                        value = LEAGUE_AVG_SLG * float(multiplier)
                    except (TypeError, ValueError):
                        value = None
            if value is None:
                continue
            try:
                zones[name] = round(_clamp(float(value), 0.050, 1.200), 3)
            except (TypeError, ValueError):
                continue

    return zones


def normalize_traits(batter: Any) -> List[str]:
    """Converts trait records/strings into a stable list of display names."""
    if batter is None:
        return []

    raw_traits = getattr(batter, 'traits', None)
    if raw_traits is None and isinstance(batter, dict):
        raw_traits = batter.get('traits')
    if not isinstance(raw_traits, list):
        return []

    names: List[str] = []
    for trait in raw_traits:
        if isinstance(trait, str):
            names.append(trait)
        elif isinstance(trait, dict):
            name = trait.get('name') or trait.get('trait') or trait.get('id')
            if name:
                names.append(str(name))
    return names


@dataclass
class InGameBatterRatings:
    """Encapsulates in-game adjusted ratings for a batter in an active game."""
    batter_id: Any
    batter_name: str
    handedness: str
    batter_side: str
    power: float
    contact: float
    vision: float
    speed: float
    effective_contact: float
    effective_discipline: float
    hot_zones: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'batter_id': self.batter_id,
            'batter_name': self.batter_name,
            'handedness': self.handedness,
            'batter_side': self.batter_side,
            'power': round(self.power, 1),
            'contact': round(self.contact, 1),
            'vision': round(self.vision, 1),
            'speed': round(self.speed, 1),
            'effective_contact': round(self.effective_contact, 1),
            'effective_discipline': round(self.effective_discipline, 1),
            'hot_zones': dict(self.hot_zones),
        }


class BatterInstanceManager:
    """Calculates in-game situational ratings without mutating player records."""

    @classmethod
    def get_adjusted_ratings(
        cls,
        batter: Any,
        balls: int = 0,
        strikes: int = 0,
        pitcher_hand: str = 'R',
    ) -> InGameBatterRatings:
        if batter is None:
            batter_id, batter_name = None, 'Batter'
        elif isinstance(batter, dict):
            batter_id = batter.get('id')
            batter_name = str(batter.get('name') or 'Batter')
        else:
            batter_id = getattr(batter, 'id', None)
            batter_name = str(getattr(batter, 'name', None) or 'Batter')

        power = _raw_batter_value(batter, 'power', DEFAULT_BATTER_RATINGS['power'])
        contact = _raw_batter_value(batter, 'contact', DEFAULT_BATTER_RATINGS['contact'])
        vision = _raw_batter_value(batter, 'vision', DEFAULT_BATTER_RATINGS['vision'])
        speed = _raw_batter_value(batter, 'speed', DEFAULT_BATTER_RATINGS['speed'])

        handedness = get_batter_hand(batter)
        batter_side = get_effective_batter_side(batter, pitcher_hand)
        pitcher_side = 'L' if str(pitcher_hand).upper().startswith('L') else 'R'

        # Small platoon adjustment when the batter has the opposite hand.
        platoon = 2.0 if batter_side != pitcher_side else 0.0
        effective_contact = contact + platoon
        # Count leverage (including two-strike protection) lives in the swing
        # model, so discipline is the batter's raw vision here.
        effective_discipline = vision

        raw_zones = None
        if isinstance(batter, dict):
            raw_zones = batter.get('zones') or batter.get('hot_zones')
        else:
            raw_zones = getattr(batter, 'zones', None) or getattr(batter, 'hot_zones', None)

        return InGameBatterRatings(
            batter_id=batter_id,
            batter_name=batter_name,
            handedness=handedness,
            batter_side=batter_side,
            power=max(20.0, min(105.0, power)),
            contact=max(20.0, min(105.0, contact)),
            vision=max(20.0, min(105.0, vision)),
            speed=max(20.0, min(105.0, speed)),
            effective_contact=effective_contact,
            effective_discipline=effective_discipline,
            hot_zones=normalize_hot_zones(raw_zones),
        )
