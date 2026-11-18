"""
Platoon & Arsenal Matchup Engine for Pitch Selection.

Evaluates the synergy between a pitcher's repertoire and an opposing batter's
profile (handedness, platoon splits, Statcast metrics, and hot/cold zones)
to establish an authoritative, pre-baked game plan.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..pitcher_info.pitch_objects import PITCH_CATEGORIES, PitchArsenal


def _extract_player_val(player: Any, *keys: str) -> Any:
    """Extract a vital attribute exclusively from player.vitals without checking top-level attributes."""
    if player is None:
        return None
    vitals = player.get('vitals') if isinstance(player, dict) else getattr(player, 'vitals', None)
    if isinstance(vitals, dict):
        for k in keys:
            v = vitals.get(k)
            if v is not None:
                return v
    elif vitals is not None:
        for k in keys:
            v = getattr(vitals, k, None)
            if v is not None:
                return v
    return None


_extract_player_vital = _extract_player_val


@dataclass(frozen=True)
class BatterMatchupPlan:
    """Pre-computed tactical matchup profile between a pitcher and a specific batter."""

    batter_id: Any
    batter_name: str
    pitcher_hand: str  # 'R' or 'L'
    batter_side: str   # 'R' or 'L' (switch hitters resolved)
    platoon_advantage: str  # 'PITCHER', 'BATTER', or 'NEUTRAL'
    pitch_base_weights: Dict[str, float]
    primary_weapon: str
    putaway_weapon: str
    grounder_weapon: str
    cold_zones: List[str]
    hot_zones: List[str]
    recommended_attack_zone: str


def evaluate_platoon_and_arsenal(
    pitcher: Any,
    batter: Any,
    arsenal: Optional[PitchArsenal] = None,
) -> BatterMatchupPlan:
    """
    Evaluates the platoon splits, repertoire multipliers, and target attack zones
    for a pitcher facing a batter.
    """
    # 1. Resolve Handedness
    raw_p_hand = _extract_player_val(pitcher, 'throws', 'handedness') or 'R'
    pitcher_hand = 'L' if str(raw_p_hand).upper().startswith('L') else 'R'

    raw_b_hand = _extract_player_val(batter, 'bats', 'handedness') or 'R'
    b_hand_str = str(raw_b_hand).upper()
    if b_hand_str.startswith('S'):
        # Switch hitter bats opposite the pitcher's throwing arm
        batter_side = 'L' if pitcher_hand == 'R' else 'R'
    else:
        batter_side = 'L' if b_hand_str.startswith('L') else 'R'

    # Same handedness gives pitcher advantage; opposite gives batter advantage
    is_same_hand = (pitcher_hand == batter_side)
    platoon_advantage = 'PITCHER' if is_same_hand else 'BATTER'

    # 2. Extract Pitch Arsenal
    if arsenal is None:
        arsenal = PitchArsenal.extract_from_pitcher(pitcher)

    raw_pitches = arsenal.to_raw_list() if arsenal else []
    if not raw_pitches:
        raw_pitches = [
            {'name': '4-Seam Fastball', 'category': 'FASTBALL', 'usage_pct': 0.50},
            {'name': 'Slider', 'category': 'BREAKING', 'usage_pct': 0.50},
        ]

    # 3. Compute Platoon & Statcast Adjusted Base Weights
    pitch_weights: Dict[str, float] = {}
    putaway_scores: Dict[str, float] = {}
    grounder_scores: Dict[str, float] = {}

    for p in raw_pitches:
        p_name = p.get('pitch') or p.get('name') or '4-Seam Fastball'
        category = p.get('category') or PITCH_CATEGORIES.get(p_name, 'Fastball')
        cat_upper = str(category).upper()

        # Check explicit split usage first
        if batter_side == 'R' and p.get('usage_pct_vs_rhb') is not None:
            w = float(p['usage_pct_vs_rhb'])
        elif batter_side == 'L' and p.get('usage_pct_vs_lhb') is not None:
            w = float(p['usage_pct_vs_lhb'])
        else:
            w = float(p.get('usage_pct') or 0.25)
            # Apply tactical platoon modifiers
            if is_same_hand:
                # Same-handed: breaking pitches moving away have high whiff/chase
                if 'BREAKING' in cat_upper or 'SLIDER' in p_name.upper() or 'SWEEPER' in p_name.upper():
                    w *= 1.25
                elif 'OFFSPEED' in cat_upper or 'CHANGEUP' in p_name.upper():
                    w *= 0.85
            else:
                # Opposite-handed: offspeed fading away or backfoot cutters dominate
                if 'OFFSPEED' in cat_upper or 'CHANGEUP' in p_name.upper() or 'SPLITTER' in p_name.upper():
                    w *= 1.30
                elif 'SWEEPER' in p_name.upper():
                    # Sweeper running into opposite-hand bat path carries higher home run risk
                    w *= 0.75
                elif 'CUTTER' in p_name.upper() or 'FASTBALL' in cat_upper:
                    w *= 1.10

        # Incorporate Statcast metrics if present
        statcast = p.get('statcast') or {}
        whiff = float(statcast.get('whiff_pct') or 25.0)
        gb = float(statcast.get('gb_pct') or 40.0)
        stuff = float(statcast.get('stuff_plus') or 100.0)

        if stuff > 120:
            w *= 1.10

        pitch_weights[p_name] = max(0.05, round(w, 3))
        putaway_scores[p_name] = whiff * (1.2 if is_same_hand and 'BREAKING' in cat_upper else 1.0)
        grounder_scores[p_name] = gb * (1.3 if 'SINKER' in p_name.upper() else 1.0)

    # 4. Resolve Tactical Weapons
    primary_weapon = max(pitch_weights, key=pitch_weights.get) if pitch_weights else '4-Seam Fastball'
    putaway_weapon = max(putaway_scores, key=putaway_scores.get) if putaway_scores else primary_weapon
    grounder_weapon = max(grounder_scores, key=grounder_scores.get) if grounder_scores else primary_weapon

    # 5. Batter Hot & Cold Zones
    if isinstance(batter, dict):
        hot_zones_data = batter.get('hot_zones') or batter.get('zones') or {}
        b_id = batter.get('id')
        b_name = str(batter.get('name') or 'Batter')
    else:
        hot_zones_data = getattr(batter, 'hot_zones', None) or getattr(batter, 'zones', None) or {}
        b_id = getattr(batter, 'id', None)
        b_name = str(getattr(batter, 'name', None) or 'Batter')

    cold_zones: List[str] = []
    hot_zones: List[str] = []

    ALL_ZONES = [
        'upper-in', 'upper-middle', 'upper-away',
        'middle-in', 'heart', 'middle-away',
        'lower-in', 'lower-middle', 'lower-away',
        'chase-high', 'chase-low', 'chase-in', 'chase-away',
    ]

    for z in ALL_ZONES:
        slg = hot_zones_data.get(z, 0.32) if isinstance(hot_zones_data, dict) else 0.32
        if slg >= 0.50:
            hot_zones.append(z)
        elif slg <= 0.28 or z in ('lower-away', 'middle-away'):
            cold_zones.append(z)

    # Default attack zone: lower-away or first cold strike zone
    attack_zone = 'lower-away'
    if 'lower-away' not in cold_zones:
        for cz in cold_zones:
            if not cz.startswith('chase-'):
                attack_zone = cz
                break

    return BatterMatchupPlan(
        batter_id=b_id,
        batter_name=b_name,
        pitcher_hand=pitcher_hand,
        batter_side=batter_side,
        platoon_advantage=platoon_advantage,
        pitch_base_weights=pitch_weights,
        primary_weapon=primary_weapon,
        putaway_weapon=putaway_weapon,
        grounder_weapon=grounder_weapon,
        cold_zones=cold_zones,
        hot_zones=hot_zones,
        recommended_attack_zone=attack_zone,
    )
