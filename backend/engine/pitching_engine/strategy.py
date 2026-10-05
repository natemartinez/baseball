"""
Pitch Strategy & Repertoire Selection for Pitching Engine.
Calculates count leverage, dynamic adaptation decay (W_t),
situational multipliers, and normalized pitch selection probabilities.
"""

import random
from typing import Dict, Any, Tuple, Optional, List

from .pitch_objects import PITCH_CATEGORIES, PitchArsenal, Pitch


class PitchStrategy:
    """Evaluates count leverage and selects pitches based on arsenal usage and context."""

    def __init__(self, pitcher: Any, batter: Any):
        self.pitcher = pitcher
        self.batter = batter
        self.arsenal_obj = PitchArsenal.extract_from_pitcher(pitcher)
        self.pitch_arsenal = self.arsenal_obj.to_raw_list()

    def get_leverage_state(self, balls: int, strikes: int) -> str:
        """Determines the tactical leverage category from count."""
        if balls == 3 and strikes == 2:
            return 'FULL_COUNT'
        elif strikes == 2 and balls < 2:
            return 'AHEAD_TWO_STRIKES'
        elif strikes > balls:
            return 'AHEAD'
        elif balls > strikes:
            return 'BEHIND'
        elif balls == 0 and strikes == 0:
            return 'FIRST_PITCH'
        return 'NEUTRAL'

    def choose_pitch(
        self,
        balls: int,
        strikes: int,
        situation: str = 'NEUTRAL',
        preferred_intent: Optional[str] = None,
        recent_pitches: Optional[List[str]] = None,
        double_play_situation: bool = False
    ) -> Dict[str, Any]:
        """
        Returns the chosen pitch, expected velocity/spin, recommended target zone, 
        and tactical rationale for the given game state.
        """
        leverage = self.get_leverage_state(balls, strikes)
        recent = recent_pitches or []

        if double_play_situation:
            situation = 'DOUBLE_PLAY'

        # 1. Base weights from arsenal usage
        raw_weights: Dict[str, float] = {}
        for p in self.pitch_arsenal:
            p_name = p.get('pitch') or p.get('name') or '4-Seam Fastball'
            usage = float(p.get('usage_pct') or p.get('usage_pct_vs_rhb') or 0.25)
            raw_weights[p_name] = max(0.05, usage)

        # 2. Count leverage adjustments
        strategy_name = 'NEUTRAL_MIX'
        rationale = 'Balanced repertoire sequencing to keep batter timing off.'
        recommended_zone = 'lower-away'

        if leverage == 'FIRST_PITCH':
            strategy_name = 'FIRST_PITCH_ESTABLISH'
            rationale = 'Establish count leverage with high-velocity primary fastball or power sinker on shadow perimeter.'
            recommended_zone = 'lower-away'
            for p_name in raw_weights:
                cat = PITCH_CATEGORIES.get(p_name, 'Fastball')
                if cat == 'Fastball':
                    raw_weights[p_name] *= 1.4

        elif leverage == 'AHEAD_TWO_STRIKES':
            strategy_name = 'TWO_STRIKE_PUT_AWAY'
            rationale = 'Put-away sequence: heavily expand chase corridors with high-spin sweeper or curveball.'
            recommended_zone = 'chase-away'
            for p_name in raw_weights:
                cat = PITCH_CATEGORIES.get(p_name, 'Breaking')
                if cat == 'Breaking':
                    raw_weights[p_name] *= 3.0
                elif cat == 'Fastball':
                    raw_weights[p_name] *= 0.50

        elif leverage == 'BEHIND':
            strategy_name = 'CRITICAL_ZONE_CHALLENGE'
            rationale = 'Behind in count: challenge the zone with high-velocity heat or sinking action to avoid walks.'
            recommended_zone = 'heart'
            for p_name in raw_weights:
                cat = PITCH_CATEGORIES.get(p_name, 'Fastball')
                if cat == 'Fastball':
                    raw_weights[p_name] *= 2.6
                else:
                    raw_weights[p_name] *= 0.35

        elif leverage == 'FULL_COUNT':
            strategy_name = 'FULL_COUNT_BATTLE'
            rationale = 'Full count leverage: balance swing-and-miss stuff against the penalty of ball 4.'
            recommended_zone = 'lower-away'
            for p_name in raw_weights:
                if 'Fastball' in p_name or 'Sinker' in p_name:
                    raw_weights[p_name] *= 1.8
                elif 'Sweeper' in p_name:
                    raw_weights[p_name] *= 1.5

        # 3. Situational multipliers
        if situation in ('DOUBLE_PLAY', 'DOUBLE_PLAY_SITUATION'):
            strategy_name = 'DOUBLE_PLAY_HUNT'
            rationale = 'Runner on 1st with < 2 outs: heavily bias toward sinking action low in the zone to induce 6-4-3 ground ball.'
            recommended_zone = 'lower-middle'
            for p_name in raw_weights:
                if 'Sinker' in p_name:
                    raw_weights[p_name] *= 2.8
                elif 'Curve' in p_name:
                    raw_weights[p_name] *= 1.4
                elif 'Fastball' in p_name:
                    raw_weights[p_name] *= 0.45

        # 4. Dynamic decay W_t (penalize repetitive pitches in sequence)
        dynamic_modifier = 1.0
        if recent and len(recent) >= 1:
            last_pitch = recent[-1]
            if last_pitch in raw_weights:
                raw_weights[last_pitch] *= 0.75
                dynamic_modifier = 0.75

        # 5. Normalize probabilities
        total_w = sum(raw_weights.values()) or 1.0
        probs = {k: round(v / total_w, 3) for k, v in raw_weights.items()}

        # 6. Weighted selection
        pitches = list(probs.keys())
        weights = list(probs.values())
        selected = random.choices(pitches, weights=weights, k=1)[0]

        # Get profile data for selected pitch
        vel = 94.0
        spin = 2400
        for p in self.pitch_arsenal:
            name = p.get('pitch') or p.get('name')
            if name == selected:
                vel = float(p.get('velocity_mph') or p.get('avg_velo_mph') or 94.0)
                spin = int(p.get('spin_rpm') or p.get('avg_spin_rpm') or 2400)
                break

        return {
            'selected_pitch': selected,
            'velocity_mph': vel,
            'spin_rpm': spin,
            'repertoire_probabilities': probs,
            'dynamic_modifier': dynamic_modifier,
            'strategy_name': strategy_name,
            'rationale': rationale,
            'recommended_zone': recommended_zone
        }
