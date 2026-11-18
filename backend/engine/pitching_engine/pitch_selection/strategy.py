"""
Pitch Strategy & Repertoire Selection for Pitching Engine.

Calculates count leverage, dynamic adaptation decay (W_t),
situational multipliers, and normalized pitch selection probabilities.
Serves as the single authoritative brain for both AI pitch selection
and user pitch recommendations.
"""

import random
from typing import Any, Dict, List, Optional

from ..pitcher_info.pitch_objects import PITCH_CATEGORIES, PitchArsenal
from .intent import pitch_specific_zone
from .matchup import BatterMatchupPlan, evaluate_platoon_and_arsenal


ALL_ZONES = [
    'upper-in', 'upper-middle', 'upper-away',
    'middle-in', 'heart', 'middle-away',
    'lower-in', 'lower-middle', 'lower-away',
    'chase-high', 'chase-low', 'chase-in', 'chase-away',
]

RULEBOOK_STRIKES = {
    'upper-in', 'upper-middle', 'upper-away',
    'middle-in', 'heart', 'middle-away',
    'lower-in', 'lower-middle', 'lower-away',
}


class PitchStrategy:
    """Evaluates count leverage and selects pitches based on arsenal usage and context of batter and situation."""

    def __init__(
        self,
        pitcher: Any,
        batter: Any,
        rng: Optional[random.Random] = None,
        arsenal: Optional[PitchArsenal] = None,
        active_state: Optional[Any] = None,
        matchup_plan: Optional[BatterMatchupPlan] = None,
    ):
        self.pitcher = pitcher
        self.batter = batter
        self.rng = rng or random
        self.arsenal_obj = arsenal or PitchArsenal.extract_from_pitcher(pitcher)
        self.pitch_arsenal = self.arsenal_obj.to_raw_list()
        self.active_state = active_state

        if matchup_plan is not None:
            self.matchup_plan = matchup_plan
        elif active_state is not None and hasattr(active_state, 'get_matchup_plan'):
            self.matchup_plan = active_state.get_matchup_plan(batter)
        else:
            self.matchup_plan = evaluate_platoon_and_arsenal(
                self.pitcher, self.batter, self.arsenal_obj
            )

    def evaluate_matchup(self) -> BatterMatchupPlan:
        """Returns the pre-baked platoon and repertoire matchup plan."""
        return self.matchup_plan

    def get_leverage_state(self, balls: int, strikes: int) -> str:
        """Determines the tactical leverage category from count."""
        if balls == 3 and strikes == 2:
            return 'FULL_COUNT'
        elif balls == 2 and strikes == 2:
            return 'TWO_TWO_COUNT'
        elif strikes == 2:
            return 'AHEAD_TWO_STRIKES'
        elif strikes > balls:
            return 'AHEAD'
        elif balls > strikes:
            return 'BEHIND'
        elif balls == 0 and strikes == 0:
            return 'FIRST_PITCH'
        return 'NEUTRAL'

    def build_plan(
        self,
        balls: int,
        strikes: int,
        situation: str = 'NEUTRAL',
        recent_pitches: Optional[List[str]] = None,
        double_play_situation: bool = False,
        outs: int = 0,
        bases: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Deterministically evaluates the tactical plan for the current state:
        leverage, arsenal weights, normalized probabilities, strategy name,
        rationale, and the recommended target zone. This performs no random
        draws, so callers can inspect the plan without disturbing RNG order.
        """
        leverage = self.get_leverage_state(balls, strikes)
        recent = recent_pitches or []

        # Resolve situational context
        is_bases_loaded = situation == 'BASES_LOADED'
        is_double_play = double_play_situation or situation in ('DOUBLE_PLAY', 'DOUBLE_PLAY_SITUATION')
        is_scoring_pos = situation == 'SCORING_POSITION'

        if bases:
            is_bases_loaded = bases.get('first') is not None and bases.get('second') is not None and bases.get('third') is not None
            is_double_play = bases.get('first') is not None and outs < 2
            is_scoring_pos = (bases.get('second') is not None or bases.get('third') is not None) and outs < 2

        if is_bases_loaded:
            situation_tag = 'BASES_LOADED'
        elif is_double_play:
            situation_tag = 'DOUBLE_PLAY_SITUATION'
        elif is_scoring_pos:
            situation_tag = 'SCORING_POSITION'
        else:
            situation_tag = 'BASES_EMPTY'

        is_full_count = balls == 3 and strikes == 2
        is_two_two = balls == 2 and strikes == 2
        is_ahead = strikes == 2 and not is_full_count and not is_two_two
        is_behind = (balls == 3 and strikes < 2) or (balls == 2 and strikes == 0)

        if is_ahead:
            count_context = f'AHEAD ({balls}-{strikes}) - PUT AWAY MODE'
        elif is_two_two:
            count_context = f'TWO-TWO BATTLE ({balls}-{strikes}) - HIGH LEVERAGE'
        elif is_behind:
            count_context = f'BEHIND ({balls}-{strikes}) - STRIKE DEMAND'
        elif is_full_count:
            count_context = 'FULL COUNT (3-2) - HIGH LEVERAGE BATTLE'
        elif balls == 0 and strikes == 0:
            count_context = 'FIRST PITCH (0-0) - ESTABLISH COUNT'
        else:
            count_context = f'NEUTRAL ({balls}-{strikes}) - SETUP & ATTACK'

        # 1. Base weights from pre-baked matchup plan
        raw_weights: Dict[str, float] = {}
        for p in self.pitch_arsenal:
            p_name = p.get('pitch') or p.get('name') or '4-Seam Fastball'
            base_w = self.matchup_plan.pitch_base_weights.get(p_name)
            if base_w is None:
                base_w = float(p.get('usage_pct') or p.get('usage_pct_vs_rhb') or 0.25)
            raw_weights[p_name] = max(0.05, float(base_w))

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
            rationale = f'Ahead in count ({balls}-{strikes}). Expand chase corridors with {self.matchup_plan.putaway_weapon}.'
            recommended_zone = 'chase-away'
            for p_name in raw_weights:
                cat = PITCH_CATEGORIES.get(p_name, 'Breaking')
                if cat == 'Breaking':
                    raw_weights[p_name] *= 3.0
                elif cat == 'Fastball':
                    raw_weights[p_name] *= 0.50
        elif leverage == 'TWO_TWO_COUNT':
            strategy_name = 'TWO_TWO_BATTLE'
            rationale = f'Two-strike count ({balls}-{strikes}). High-leverage battle: expand chase corridors with {self.matchup_plan.putaway_weapon} or elevate heat; protect against ball 3.'
            recommended_zone = 'chase-away'
            for p_name in raw_weights:
                cat = PITCH_CATEGORIES.get(p_name, 'Fastball')
                if cat == 'Breaking':
                    raw_weights[p_name] *= 2.8
                elif cat == 'Fastball':
                    raw_weights[p_name] *= 0.7
        elif leverage == 'BEHIND':
            strategy_name = 'CRITICAL_ZONE_CHALLENGE'
            rationale = f'Behind in count ({balls}-{strikes}). Challenge the zone with high-velocity heat or sinking action.'
            recommended_zone = 'heart'
            for p_name in raw_weights:
                cat = PITCH_CATEGORIES.get(p_name, 'Fastball')
                if cat == 'Fastball' or 'Sinker' in p_name:
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
                elif 'Sweeper' in p_name or 'Slider' in p_name:
                    raw_weights[p_name] *= 1.5

        # 3. Situational multipliers
        if is_bases_loaded:
            if is_ahead:
                strategy_name = 'BASES_LOADED_PUNCHOUT'
                rationale = 'Bases loaded with 2 strikes. Zero margin for error. Attack edges with high-whiff putaway arsenal to secure the strikeout.'
                for p_name in raw_weights:
                    if 'Sweeper' in p_name or 'Curve' in p_name or 'Slider' in p_name:
                        raw_weights[p_name] *= 2.5
            elif is_behind:
                strategy_name = 'BASES_LOADED_COMMAND_STRIKE'
                rationale = 'Bases loaded behind in count. Ball 4 forces home a run! Must challenge the zone with high-velocity 4-Seamer or Sinker.'
                for p_name in raw_weights:
                    if 'Fastball' in p_name or 'Sinker' in p_name:
                        raw_weights[p_name] *= 2.2
                    else:
                        raw_weights[p_name] *= 0.4
            else:
                strategy_name = 'BASES_LOADED_LEVERAGE'
                rationale = 'Bases loaded pressure. Induce weak ground-ball or foul contact to prevent extra-base damage.'
                recommended_zone = 'lower-middle'
        elif is_double_play:
            strategy_name = 'DOUBLE_PLAY_GROUNDER_HUNT'
            rationale = f'Runner on 1st with {outs} out. Target bottom of zone with {self.matchup_plan.grounder_weapon} to roll double play.'
            recommended_zone = 'lower-middle'
            for p_name in raw_weights:
                if 'Sinker' in p_name:
                    raw_weights[p_name] *= 2.8
                elif 'Curve' in p_name or 'Changeup' in p_name:
                    raw_weights[p_name] *= 1.3
                elif 'Fastball' in p_name:
                    raw_weights[p_name] *= 0.45
        elif is_scoring_pos and not is_ahead:
            strategy_name = 'SCORING_POSITION_SUPPRESSION'
            rationale = f'Runner in scoring position with {outs} out. Suppress elevated contact to avoid sacrifice fly; attack batter cold zones.'
            recommended_zone = 'lower-away'

        # 3. Dynamic sequence decay (consecutive repetition penalty)
        dynamic_modifier = 1.0
        if recent and len(recent) >= 1:
            last_pitch = recent[-1]
            consecutive_count = 0
            for p in reversed(recent):
                if p == last_pitch:
                    consecutive_count += 1
                else:
                    break

            if last_pitch in raw_weights:
                if consecutive_count == 1:
                    decay = 0.75  # 1 prior throw: doubling up allowed (~20-25% chance)
                elif consecutive_count == 2:
                    decay = 0.20  # 2 prior throws: tripling up suppressed (~5% chance)
                else:
                    decay = 0.02  # 3+ prior throws: practically eliminated (<1% chance)
                raw_weights[last_pitch] *= decay
                dynamic_modifier *= decay

        # 4. Cross-at-bat history decay (from ActivePitcherState)
        if self.active_state and hasattr(self.active_state, 'at_bat_history'):
            key = getattr(self.active_state, '_batter_key', lambda b: getattr(b, 'id', None))(self.batter)
            prior_pitches = self.active_state.at_bat_history.get(key, [])
            if len(prior_pitches) >= 3 and len(set(prior_pitches[-3:])) == 1:
                repeated_pitch = prior_pitches[-1]
                if repeated_pitch in raw_weights:
                    raw_weights[repeated_pitch] *= 0.85
                    dynamic_modifier *= 0.95

        # 5. Normalize probabilities & Rank pitches
        total_w = sum(raw_weights.values()) or 1.0
        probs = {k: round(v / total_w, 3) for k, v in raw_weights.items()}

        sorted_pitches = sorted(raw_weights.items(), key=lambda x: x[1], reverse=True)
        ranked_pitch_weights: List[Dict[str, Any]] = []
        for idx, (p_name, w) in enumerate(sorted_pitches):
            prob = (w / total_w) * 100.0
            if idx == 0 and is_double_play:
                reason = f'Primary weapon: roll double play with {p_name}'
            elif idx == 0 and is_ahead:
                reason = f'Putaway weapon: high-whiff strikeout pitch {p_name}'
            elif idx == 0 and is_behind:
                reason = f'Strike demand: zone command with {p_name}'
            elif idx == len(sorted_pitches) - 1:
                reason = 'Deprioritized in current game leverage'
            else:
                reason = 'Secondary tactical option'

            # Find matching raw pitch statcast
            statcast_data = {}
            for p in self.pitch_arsenal:
                name = p.get('pitch') or p.get('name')
                if name == p_name:
                    statcast_data = p.get('statcast', {})
                    break

            ranked_pitch_weights.append({
                'pitch_name': p_name,
                'weight': round(w, 1),
                'probability_pct': round(prob, 1),
                'rank': idx + 1,
                'is_most_likely': (idx == 0),
                'is_least_likely': (idx == len(sorted_pitches) - 1),
                'reasoning': reason,
                'statcast': statcast_data,
            })

        # Top pitch that the CPU would choose
        top_pitch = ranked_pitch_weights[0]['pitch_name'] if ranked_pitch_weights else '4-Seam Fastball'

        # 6. Evaluate all 13 zones
        zone_weights_raw = []
        cold_set = set(self.matchup_plan.cold_zones)
        hot_set = set(self.matchup_plan.hot_zones)

        for zone in ALL_ZONES:
            zw = 10.0
            zone_is_strike = zone in RULEBOOK_STRIKES
            is_chase = not zone_is_strike

            if zone in hot_set:
                zone_type = 'HOT_ZONE'
                if is_behind and balls == 3 and strikes < 2:
                    zw *= 0.7
                else:
                    zw *= 0.22
            elif zone in cold_set or zone in ('lower-away', 'middle-away'):
                zone_type = 'COLD_ZONE'
                zw *= 2.4
            elif is_chase:
                zone_type = 'CHASE_ZONE'
            else:
                zone_type = 'NEUTRAL_ZONE'

            if is_full_count:
                if is_chase:
                    zw *= 0.15
                else:
                    zw *= 2.2
            elif is_ahead:
                if is_chase:
                    zw *= 3.4
                elif zone == 'heart':
                    zw *= 0.12
            elif is_two_two:
                if is_chase:
                    zw *= 2.6
                elif zone == 'heart':
                    zw *= 0.2
                else:
                    zw *= 1.8
            elif is_behind:
                if is_chase:
                    zw *= 0.12
                else:
                    zw *= 2.0

            if is_double_play:
                if zone in ('lower-in', 'lower-middle', 'lower-away'):
                    zw *= 3.0
                elif zone == 'chase-low':
                    zw *= 2.6
                elif zone in ('upper-in', 'upper-middle', 'upper-away', 'chase-high'):
                    zw *= 0.3

            if is_bases_loaded and is_chase:
                zw *= 0.25

            zone_weights_raw.append({
                'zone': zone,
                'zw': zw,
                'zone_is_strike': zone_is_strike,
                'zone_type': zone_type,
            })

        total_zone_w = sum(x['zw'] for x in zone_weights_raw) or 1.0
        sorted_zones = sorted(zone_weights_raw, key=lambda x: x['zw'], reverse=True)
        ranked_zone_weights = []
        for idx, zw_dict in enumerate(sorted_zones):
            z = zw_dict['zone']
            zw = zw_dict['zw']
            prob = (zw / total_zone_w) * 100.0
            ranked_zone_weights.append({
                'zone': z,
                'weight': round(zw, 1),
                'probability_pct': round(prob, 1),
                'rank': idx + 1,
                'is_strike': zw_dict['zone_is_strike'],
                'zone_type': zw_dict['zone_type'],
                'is_most_likely': (idx == 0),
                'is_least_likely': (idx == len(sorted_zones) - 1),
            })

        top_zone = recommended_zone

        return {
            'strategy_name': strategy_name,
            'situation_tag': situation_tag,
            'count_context': count_context,
            'rationale': rationale,
            'recommended_pitch': top_pitch,
            'recommended_zone': top_zone,
            'pitch_weights': ranked_pitch_weights,
            'zone_weights': ranked_zone_weights,
            'command_quality': 'TARGET_EXECUTED',
            'repertoire_probabilities': probs,
            'dynamic_modifier': round(dynamic_modifier, 3),
        }

    def choose_pitch(
        self,
        balls: int,
        strikes: int,
        situation: str = 'NEUTRAL',
        recent_pitches: Optional[List[str]] = None,
        double_play_situation: bool = False,
    ) -> Dict[str, Any]:
        """
        Returns the chosen pitch, expected velocity/spin, recommended target zone,
        and tactical rationale for the given game state.

        The weighted draw is the first RNG call so seeded AI outcomes remain
        identical to the previous implementation.
        """
        plan = self.build_plan(
            balls=balls,
            strikes=strikes,
            situation=situation,
            recent_pitches=recent_pitches,
            double_play_situation=double_play_situation,
        )

        probs = plan['repertoire_probabilities']
        pitches = list(probs.keys())
        weights = list(probs.values())
        selected = self.rng.choices(pitches, weights=weights, k=1)[0]

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
            **plan,
        }


def calculate_strategy_and_intent(
    outs: int,
    balls: int,
    strikes: int,
    bases: Dict[str, Any],
    batter: Any,
    pitcher: Any,
    active_state: Optional[Any] = None,
    pitch_sequence: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Direct facade over PitchStrategy.build_plan() for generating the UI strategy
    and pitch recommendations payload.
    """
    strategy = PitchStrategy(
        pitcher=pitcher,
        batter=batter,
        active_state=active_state,
    )
    is_bases_loaded = bases.get('first') is not None and bases.get('second') is not None and bases.get('third') is not None
    is_double_play = bases.get('first') is not None and outs < 2
    is_scoring_pos = (bases.get('second') is not None or bases.get('third') is not None) and outs < 2

    if is_bases_loaded:
        situation = 'BASES_LOADED'
    elif is_double_play:
        situation = 'DOUBLE_PLAY'
    elif is_scoring_pos:
        situation = 'SCORING_POSITION'
    else:
        situation = 'NEUTRAL'

    recent_pitches: List[str] = []
    last_pitch_name: Optional[str] = None
    last_target_zone: Optional[str] = None

    if pitch_sequence and len(pitch_sequence) >= 1:
        recent_pitches = [
            str(p.get('pitch_name') or p.get('selected_pitch'))
            for p in pitch_sequence
            if isinstance(p, dict) and (p.get('pitch_name') or p.get('selected_pitch'))
        ]
        last_entry = pitch_sequence[-1]
        if isinstance(last_entry, dict):
            last_pitch_name = last_entry.get('pitch_name') or last_entry.get('selected_pitch')
            last_target_zone = (
                last_entry.get('target_zone')
                or last_entry.get('nominal_zone')
                or last_entry.get('zone_name')
            )

    plan = strategy.build_plan(
        balls=balls,
        strikes=strikes,
        situation=situation,
        recent_pitches=recent_pitches,
        double_play_situation=is_double_play,
        outs=outs,
        bases=bases,
    )
    # For UI recommendation display, apply pitch-specific zone bias to recommended pitch
    plan['recommended_zone'] = pitch_specific_zone(
        plan['recommended_zone'],
        plan['recommended_pitch'],
        pitcher_hand=strategy.matchup_plan.pitcher_hand,
        batter_side=strategy.matchup_plan.batter_side,
        last_pitch_name=last_pitch_name,
        last_target_zone=last_target_zone,
    )
    recommendation_keys = {
        'strategy_name',
        'situation_tag',
        'count_context',
        'rationale',
        'recommended_pitch',
        'recommended_zone',
        'pitch_weights',
        'zone_weights',
        'command_quality',
    }
    return {k: v for k, v in plan.items() if k in recommendation_keys}
