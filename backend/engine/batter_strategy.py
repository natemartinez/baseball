"""
MLB Statcast Batter Strategy & Collision Engine.
Evaluates batter swing decisions, hot-zone damage potential, count-based discipline,
and batted-ball collision physics (exit velocity, launch angle, hit/out resolution).
"""

import random
from typing import Dict, Any, Tuple, Optional

JUDGE_DEFAULT_ZONES = {
    'upper-in': 0.650,
    'upper-middle': 0.510,
    'upper-away': 0.350,
    'middle-in': 0.540,
    'heart': 0.820,
    'middle-away': 0.280,
    'lower-in': 0.380,
    'lower-middle': 0.420,
    'lower-away': 0.240,
    'chase-high': 0.180,
    'chase-low': 0.150,
    'chase-in': 0.190,
    'chase-away': 0.170,
}


class BatterStrategy:
    def __init__(self, batter: Any = None):
        # Enforce domain model boundary
        if isinstance(batter, dict):
            try:
                from backend.models.player import Player
                batter = Player.from_dict(batter)
            except ImportError:
                pass

        self.batter = batter
        self.hot_zones: Dict[str, float] = {}
        if batter:
            raw_zones = getattr(batter, 'zones', None)
            if isinstance(raw_zones, dict):
                self.hot_zones = {k: float(v) for k, v in raw_zones.items()}
            elif isinstance(raw_zones, list):
                for z in raw_zones:
                    if isinstance(z, dict) and 'zone' in z and 'slugging' in z:
                        self.hot_zones[z['zone']] = float(z['slugging'])

        if not self.hot_zones:
            self.hot_zones = dict(JUDGE_DEFAULT_ZONES)


    def decide_swing(
        self,
        zone_category: str,
        actual_zone_name: str,
        is_strike: bool,
        balls: int,
        strikes: int,
        approach_mode: str = 'AUTO'
    ) -> Tuple[bool, float]:
        """
        Returns (will_swing: bool, swing_probability: float).
        """
        # Base probability by zone category
        if zone_category == 'HEART':
            prob = 0.88
        elif zone_category == 'SHADOW':
            prob = 0.58 if is_strike else 0.42
        elif zone_category == 'CHASE':
            prob = 0.22
        else:  # WASTE
            prob = 0.04

        # Hot zone boost
        slugging = self.hot_zones.get(actual_zone_name, 0.350)
        if slugging >= 0.600:
            prob += 0.10
        elif slugging <= 0.250:
            prob -= 0.08

        # Count adjustments
        if balls == 3 and strikes == 0:
            # 3-0 Green light only on pure heart
            prob = 0.25 if zone_category == 'HEART' else 0.02
        elif balls == 0 and strikes == 0:
            # 0-0 take tendency
            prob *= 0.85
        elif strikes == 2:
            # Protect with 2 strikes
            if not is_strike:
                prob *= 1.65  # Expand chase corridor
            else:
                prob = max(prob, 0.82)

        # Approach mode overrides
        mode = (approach_mode or 'AUTO').upper()
        if mode == 'AGGRESSIVE':
            prob = min(0.98, prob + 0.15)
        elif mode == 'PATIENT':
            if not is_strike:
                prob *= 0.65
            else:
                prob *= 0.90
        elif mode == 'CONTACT':
            if is_strike:
                prob = min(0.95, prob + 0.10)

        prob = max(0.01, min(0.99, prob))
        will_swing = random.random() < prob
        return will_swing, round(prob, 3)

    def resolve_contact(
        self,
        pitch_name: str,
        velocity_mph: float,
        actual_zone_name: str,
        zone_category: str,
        is_strike: bool
    ) -> Dict[str, Any]:
        """
        Resolves a swing: Swinging Strike vs Foul vs In-Play (Single, Double, HR, Out).
        """
        slugging = self.hot_zones.get(actual_zone_name, 0.350)

        # Whiff probability
        is_breaking = 'Sweeper' in pitch_name or 'Curve' in pitch_name or 'Slider' in pitch_name
        base_whiff = 0.38 if is_breaking else 0.22
        if zone_category in ('CHASE', 'WASTE'):
            base_whiff += 0.25
        elif zone_category == 'HEART':
            base_whiff -= 0.12

        whiff_prob = max(0.08, min(0.75, base_whiff))

        roll = random.random()
        if roll < whiff_prob:
            return {
                'call': 'SWINGING_STRIKE',
                'description': f'Swinging strike on {pitch_name} ({velocity_mph} mph)',
                'is_in_play': False,
                'exit_velocity_mph': None,
                'launch_angle_deg': None
            }

        # Foul ball probability
        foul_prob = 0.42
        if (roll - whiff_prob) < foul_prob * (1.0 - whiff_prob):
            return {
                'call': 'FOUL',
                'description': f'Fouled off ({velocity_mph} mph {pitch_name})',
                'is_in_play': False,
                'exit_velocity_mph': round(random.uniform(70.0, 95.0), 1),
                'launch_angle_deg': round(random.uniform(45.0, 75.0), 1)
            }

        # Ball in Play!
        # Exit velocity & launch angle based on batter power and pitch location
        base_ev = 92.0
        if slugging >= 0.700:
            base_ev = 104.0
        elif slugging >= 0.500:
            base_ev = 98.0
        elif zone_category in ('CHASE', 'WASTE'):
            base_ev = 84.0

        ev = round(random.gauss(base_ev, 6.5), 1)
        la = round(random.gauss(18.0, 14.0), 1)

        # Outcome resolution based on EV and LA
        if ev >= 102.0 and 22.0 <= la <= 36.0:
            call = 'HOME_RUN'
            desc = f'CRUSHED! Home Run to deep center ({ev} MPH, {la}°)!'
        elif ev >= 95.0 and 10.0 <= la <= 25.0:
            call = 'DOUBLE' if random.random() < 0.45 else 'SINGLE'
            desc = f'Hard line drive into the gap ({ev} MPH, {la}°)!'
        elif ev >= 80.0 and 8.0 <= la <= 28.0:
            call = 'SINGLE'
            desc = f'Base hit into the outfield ({ev} MPH, {la}°)!'
        elif la < 8.0:
            call = 'IN_PLAY_OUT'
            desc = f'Ground ball out ({ev} MPH, {la}° launch angle).'
        elif la > 38.0:
            call = 'IN_PLAY_OUT'
            desc = f'High pop fly out ({ev} MPH, {la}° launch angle).'
        else:
            call = 'IN_PLAY_OUT'
            desc = f'Fly out caught in deep outfield ({ev} MPH, {la}°).'

        return {
            'call': call,
            'description': desc,
            'is_in_play': True,
            'exit_velocity_mph': ev,
            'launch_angle_deg': la
        }
