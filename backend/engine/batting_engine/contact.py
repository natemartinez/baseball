"""
Batted-Ball Contact & Collision Resolution.

Given a realized pitch and an in-game batter profile, resolves swing-and-miss,
fouls, and balls in play. In-play outcomes derive exit velocity, launch angle,
spray direction, and a result from the existing PitchResultType taxonomy.
"""

import random
from typing import Any, Dict, Optional

from .batters import InGameBatterRatings


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
        base = {'Fastball': 0.17, 'Breaking': 0.27, 'OffSpeed': 0.23}.get(
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
            82.0
            + self.ratings.power * 0.11
            + (slugging - 0.400) * 10.0
            + (velocity - 93.0) * 0.10
        )
        exit_velocity = round(self.rng.gauss(base_ev, 5.2), 1)
        exit_velocity = max(45.0, min(122.0, exit_velocity))

        mean_launch = 12.0 + (realized_z - 2.5) * 9.0
        if pitch_category == 'Breaking':
            mean_launch -= 4.0
        elif pitch_category == 'OffSpeed':
            mean_launch -= 2.0
        if 'Sinker' in pitch_name or 'Splitter' in pitch_name:
            mean_launch -= 4.0
        if pitch_category == 'Fastball' and realized_z >= 3.0:
            mean_launch += 4.0
        launch_angle = round(self.rng.gauss(mean_launch, 13.0), 1)
        launch_angle = max(-25.0, min(78.0, launch_angle))

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

        contact_quality = self._contact_quality(exit_velocity, launch_angle)
        call = self._classify_outcome(
            exit_velocity=exit_velocity,
            launch_angle=launch_angle,
            spray_angle=spray_angle,
        )

        return {
            'call': call,
            'description': self._describe(call, exit_velocity, launch_angle, spray_angle),
            'is_in_play': True,
            'exit_velocity_mph': exit_velocity,
            'launch_angle_deg': launch_angle,
            'spray_angle_deg': spray_angle,
            'contact_quality': contact_quality,
        }

    def _contact_quality(self, exit_velocity: float, launch_angle: float) -> str:
        if exit_velocity >= 98.0 and 12.0 <= launch_angle <= 34.0:
            return 'BARREL'
        if exit_velocity >= 88.0:
            return 'SOLID'
        return 'WEAK'

    def _classify_outcome(
        self,
        *,
        exit_velocity: float,
        launch_angle: float,
        spray_angle: float,
    ) -> str:
        speed = self.ratings.speed

        if (
            exit_velocity >= 92.0
            and 16.0 <= launch_angle <= 40.0
            and abs(spray_angle) <= 48.0
        ):
            return 'HOME_RUN'

        if (
            exit_velocity >= 92.0
            and 10.0 <= launch_angle <= 30.0
            and speed >= 78.0
            and self.rng.random() < 0.10
        ):
            return 'TRIPLE'

        if (
            exit_velocity >= 92.0
            and 8.0 <= launch_angle <= 32.0
            and self.rng.random() < 0.50
        ):
            return 'DOUBLE'
        if (
            exit_velocity >= 86.0
            and launch_angle >= 22.0
            and self.rng.random() < 0.30
        ):
            return 'DOUBLE'
        if speed >= 82.0 and launch_angle < 8.0 and self.rng.random() < 0.10:
            return 'DOUBLE'

        hit_probability = self._hit_probability(exit_velocity, launch_angle, spray_angle)
        if self.rng.random() < hit_probability:
            return 'SINGLE'
        return 'IN_PLAY_OUT'

    def _hit_probability(
        self,
        exit_velocity: float,
        launch_angle: float,
        spray_angle: float,
    ) -> float:
        """Approximate the share of non-extra-base contact that falls for a hit."""
        if exit_velocity >= 95.0:
            prob = 0.50
        elif exit_velocity >= 88.0:
            prob = 0.36
        elif exit_velocity >= 80.0:
            prob = 0.24
        elif exit_velocity >= 70.0:
            prob = 0.15
        else:
            prob = 0.08

        if launch_angle < 5.0:
            prob *= 0.72
        elif launch_angle > 40.0:
            prob *= 0.15
        elif 10.0 <= launch_angle <= 30.0:
            prob *= 1.10

        if abs(spray_angle) > 45.0:
            prob *= 0.85

        if self.ratings.speed >= 80.0 and launch_angle < 10.0:
            prob *= 1.15

        return max(0.02, min(0.80, prob))

    def _describe(
        self,
        call: str,
        exit_velocity: float,
        launch_angle: float,
        spray_angle: float,
    ) -> str:
        field = 'left-center'
        if spray_angle >= 22.0:
            field = 'right field'
        elif spray_angle <= -22.0:
            field = 'left field'

        if call == 'HOME_RUN':
            return f'CRUSHED! Home run to {field} ({exit_velocity} MPH, {launch_angle} degrees)!'
        if call == 'TRIPLE':
            return f'Triple into the gap at {field} ({exit_velocity} MPH, {launch_angle} degrees)!'
        if call == 'DOUBLE':
            return f'Line drive into the gap at {field} ({exit_velocity} MPH, {launch_angle} degrees)!'
        if call == 'SINGLE':
            return f'Base hit into {field} ({exit_velocity} MPH, {launch_angle} degrees)!'
        if launch_angle < 8.0:
            return f'Ground ball out ({exit_velocity} MPH, {launch_angle} degrees).'
        if launch_angle > 38.0:
            return f'High pop fly out ({exit_velocity} MPH, {launch_angle} degrees).'
        return f'Fly out caught in {field} ({exit_velocity} MPH, {launch_angle} degrees).'
