"""
Batted-Ball Contact & Collision Resolution.

Given a realized pitch and an in-game batter profile, resolves swing-and-miss,
fouls, and balls in play. In-play outcomes derive exit velocity, launch angle,
and spray direction from the batter/pitch model, then classify the result from
the actual landing point against each fielder's baseline reach radius.
"""

import random
from typing import Any, Dict, Optional

from .batters import InGameBatterRatings
from .contact_outcome import resolve_contact_outcome


class ContactResolver:
    """Resolves a swing into whiff, foul, or a batted-ball outcome."""

    def __init__(self, ratings: InGameBatterRatings, rng: Optional[random.Random] = None):
        self.ratings = ratings
        self.rng = rng or random

    def resolve(
        self,
        delivery: Dict[str, Any],
        actual_zone_name: str,
        balls: int = 0,
        strikes: int = 0,
        approach_mode: str = 'AUTO',
    ) -> Dict[str, Any]:
        zone_category = str(delivery.get('realized_zone_cat', 'SHADOW')).upper()
        is_strike = bool(delivery.get('is_strike', False))
        pitch_name = str(delivery.get('selected_pitch', '4-Seam Fastball'))
        pitch_category = str(delivery.get('pitch_category', 'Fastball'))
        velocity = float(delivery.get('velocity_mph', 93.0) or 93.0)
        horizontal_break = abs(float(delivery.get('horizontal_break_in', 0.0) or 0.0))
        vertical_break = abs(float(delivery.get('induced_vertical_break_in', 0.0) or 0.0))
        pitch_effectiveness = float(delivery.get('pitch_effectiveness', 50.0) or 50.0)
        realized_x = float(delivery.get('realized_x', 0.0) or 0.0)
        realized_z = float(delivery.get('realized_z', 2.5) or 2.5)

        whiff_prob = self._whiff_probability(
            zone_category=zone_category,
            is_strike=is_strike,
            pitch_category=pitch_category,
            velocity=velocity,
            movement=horizontal_break + vertical_break,
            pitch_effectiveness=pitch_effectiveness,
            balls=balls,
            strikes=strikes,
            approach_mode=approach_mode,
        )

        roll = self.rng.random()
        if roll < whiff_prob:
            return {
                'call': 'SWINGING_STRIKE',
                'description': f'Swinging strike on {pitch_name} ({velocity} mph)',
                'is_in_play': False,
                'exit_velocity_mph': None,
                'launch_angle_deg': None,
                'spray_angle_deg': None,
                'contact_quality': None,
            }

        foul_prob = self._foul_probability(zone_category, strikes)
        if roll < whiff_prob + foul_prob * (1.0 - whiff_prob):
            return {
                'call': 'FOUL',
                'description': f'Fouled off ({velocity} mph {pitch_name})',
                'is_in_play': False,
                'exit_velocity_mph': None,
                'launch_angle_deg': None,
                'spray_angle_deg': None,
                'contact_quality': None,
            }

        return self._resolve_batted_ball(
            actual_zone_name=actual_zone_name,
            pitch_name=pitch_name,
            pitch_category=pitch_category,
            velocity=velocity,
            realized_x=realized_x,
            realized_z=realized_z,
        )

    def _whiff_probability(
        self,
        *,
        zone_category: str,
        is_strike: bool,
        pitch_category: str,
        velocity: float,
        movement: float,
        pitch_effectiveness: float,
        balls: int,
        strikes: int,
        approach_mode: str,
    ) -> float:
        base = {'Fastball': 0.21, 'Breaking': 0.31, 'OffSpeed': 0.27}.get(
            pitch_category, 0.20
        )
        contact_adj = (50.0 - self.ratings.effective_contact) * 0.0030
        zone_adj = 0.0
        if zone_category in ('CHASE', 'WASTE'):
            zone_adj = 0.17
        elif zone_category == 'HEART':
            zone_adj = -0.10
        elif not is_strike:
            zone_adj = 0.05

        effectiveness_adj = max(0.0, pitch_effectiveness - 50.0) * 0.0015
        velocity_adj = (velocity - 93.0) * 0.004
        movement_adj = max(0.0, movement) * 0.0012

        mode = (approach_mode or 'AUTO').upper()
        approach_adj = 0.0
        if mode == 'CONTACT':
            approach_adj = -0.05
        elif mode == 'AGGRESSIVE':
            approach_adj = 0.03
        elif mode == 'PATIENT':
            approach_adj = -0.01

        two_strike_adj = -0.01 if strikes == 2 else 0.0
        prob = (
            base
            + contact_adj
            + zone_adj
            + effectiveness_adj
            + velocity_adj
            + movement_adj
            + approach_adj
            + two_strike_adj
        )
        return max(0.05, min(0.72, prob))

    def _foul_probability(self, zone_category: str, strikes: int) -> float:
        prob = 0.38 + (60.0 - self.ratings.effective_contact) * 0.001
        if zone_category == 'HEART':
            prob -= 0.03
        if strikes == 2:
            prob += 0.05
        return max(0.18, min(0.55, prob))

    def _resolve_batted_ball(
        self,
        *,
        actual_zone_name: str,
        pitch_name: str,
        pitch_category: str,
        velocity: float,
        realized_x: float,
        realized_z: float,
    ) -> Dict[str, Any]:
        slugging = self.ratings.hot_zones.get(actual_zone_name, 0.400)

        base_ev = (
            84.5
            + self.ratings.power * 0.145
            + (slugging - 0.400) * 13.0
            + (velocity - 93.0) * 0.13
        )
        exit_velocity = round(self.rng.gauss(base_ev, 6.8), 1)
        exit_velocity = max(45.0, min(122.0, exit_velocity))

        mean_launch = 21.0 + (realized_z - 2.5) * 9.0
        if pitch_category == 'Breaking':
            mean_launch -= 4.0
        elif pitch_category == 'OffSpeed':
            mean_launch -= 2.0
        if 'Sinker' in pitch_name or 'Splitter' in pitch_name:
            mean_launch -= 4.0
        if pitch_category == 'Fastball' and realized_z >= 3.0:
            mean_launch += 4.0
        launch_angle = round(self.rng.gauss(mean_launch, 13.0), 1)
        launch_angle = max(-10.0, min(78.0, launch_angle))

        inside = (
            (self.ratings.batter_side == 'R' and realized_x < 0.0)
            or (self.ratings.batter_side == 'L' and realized_x > 0.0)
        )
        # Positive spray = right field, negative = left field. A right-handed
        # batter pulls an inside pitch toward left field, and vice versa.
        pull_sign = -1.0 if self.ratings.batter_side == 'R' else 1.0
        pull_bias = pull_sign * (12.0 if inside else -6.0)
        spray_angle = round(self.rng.gauss(pull_bias, 16.0), 1)
        spray_angle = max(-65.0, min(65.0, spray_angle))

        # Every fair in-play ball is classified from its actual landing point.
        # A ball inside any fielder's baseline reach is an out; a ball outside
        # every radius is a hit. This keeps the visual landing and the call
        # consistent for both AI and player-controlled contact.
        outcome = resolve_contact_outcome(
            exit_velocity,
            launch_angle,
            spray_angle,
            batter_speed=self.ratings.speed,
        )
        if outcome is None:
            # Defensive fallback: valid clamped inputs should always resolve.
            return {
                'call': 'SINGLE',
                'description': 'Ball in play.',
                'is_in_play': True,
                'exit_velocity_mph': exit_velocity,
                'launch_angle_deg': launch_angle,
                'spray_angle_deg': spray_angle,
                'contact_quality': 'WEAK',
                'batted_ball': None,
            }

        return {
            'call': outcome['call'],
            'description': outcome['description'],
            'is_in_play': outcome['is_in_play'],
            'exit_velocity_mph': outcome['exit_velocity_mph'],
            'launch_angle_deg': outcome['launch_angle_deg'],
            'spray_angle_deg': outcome['spray_angle_deg'],
            'contact_quality': outcome['contact_quality'],
            'batted_ball': outcome['batted_ball'],
        }
