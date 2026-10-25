"""
MLB Statcast Batter Swing-Decision Model.

Evaluates whether a batter swings at a realized pitch using zone location,
hot/cold zone damage, vision/discipline, count leverage, approach mode, and
the pitch's execution quality. The model is deterministic given an injected
RNG and never mutates game state.
"""

import random
from typing import Any, Optional, Tuple

from .batters import InGameBatterRatings


class BatterStrategy:
    """Decides swing vs. take for a single pitch."""

    def __init__(self, ratings: Any, rng: Optional[random.Random] = None):
        if isinstance(ratings, InGameBatterRatings):
            self.ratings = ratings
        else:
            from .batters import BatterInstanceManager
            self.ratings = BatterInstanceManager.get_adjusted_ratings(ratings)
        self.rng = rng or random

    def decide_swing(
        self,
        delivery: Any,
        actual_zone_name: Optional[str] = None,
        is_strike: Optional[bool] = None,
        balls: int = 0,
        strikes: int = 0,
        approach_mode: str = 'AUTO',
    ) -> Tuple[bool, float]:
        """
        Returns (will_swing, swing_probability).

        Accepts either a pitch-delivery dict from the PitchingEngine or the
        legacy positional form (zone_category, zone_name, is_strike, balls,
        strikes).
        """
        if isinstance(delivery, dict):
            pitch = delivery
            zone_category = str(pitch.get('realized_zone_cat', 'SHADOW')).upper()
            zone_name = actual_zone_name or 'heart'
            strike = bool(pitch.get('is_strike', False))
            velocity = float(pitch.get('velocity_mph', 93.0) or 93.0)
            pitch_category = str(pitch.get('pitch_category', 'Fastball'))
            pitch_effectiveness = float(pitch.get('pitch_effectiveness', 50.0) or 50.0)
            horizontal_break = abs(float(pitch.get('horizontal_break_in', 0.0) or 0.0))
            vertical_break = abs(float(pitch.get('induced_vertical_break_in', 0.0) or 0.0))
        else:
            zone_category = str(delivery or 'SHADOW').upper()
            zone_name = actual_zone_name or 'heart'
            strike = bool(is_strike)
            velocity = 93.0
            pitch_category = 'Fastball'
            pitch_effectiveness = 50.0
            horizontal_break = 0.0
            vertical_break = 0.0

        if zone_category == 'HEART':
            prob = 0.85
        elif zone_category == 'SHADOW':
            prob = 0.58 if strike else 0.42
        elif zone_category == 'CHASE':
            prob = 0.24
        else:  # WASTE
            prob = 0.05

        # Zone damage: hitters protect/attack hot zones more aggressively.
        slugging = self.ratings.hot_zones.get(zone_name, 0.400)
        if slugging >= 0.500:
            prob += 0.08
        elif slugging <= 0.290:
            prob -= 0.06

        # Vision/discipline: better hitters swing at strikes and lay off balls.
        discipline = (self.ratings.effective_discipline - 60.0) / 40.0
        discipline = max(-1.0, min(1.0, discipline))
        if strike:
            prob += discipline * 0.06
        else:
            prob -= discipline * 0.12

        # Pitch recognition: breaking/offspeed pitches and high execution
        # suppress chase swings; velocity has a small effect.
        if pitch_category == 'Breaking':
            prob *= 0.94 if strike else 0.88
        elif pitch_category == 'OffSpeed':
            prob *= 0.97 if strike else 0.92

        if not strike:
            prob *= max(0.65, 1.0 - max(0.0, pitch_effectiveness - 50.0) / 250.0)
            prob *= max(0.80, 1.0 - ((velocity - 90.0) * 0.004))
            prob *= max(0.86, 1.0 - ((horizontal_break + vertical_break) * 0.0025))
        else:
            prob += max(0.0, (velocity - 93.0)) * 0.002

        # Count leverage.
        if balls == 3 and strikes == 0:
            prob = 0.25 if zone_category == 'HEART' else 0.02
        elif balls == 0 and strikes == 0:
            prob *= 0.90
        elif balls == 3 and strikes < 2 and not strike:
            prob *= 0.75
        elif strikes == 2:
            if not strike:
                prob *= 1.55
            else:
                prob = max(prob, 0.82)

        # Approach override.
        mode = (approach_mode or 'AUTO').upper()
        if mode == 'AGGRESSIVE':
            prob = min(0.98, prob + 0.15)
        elif mode == 'PATIENT':
            if not strike:
                prob *= 0.60
            else:
                prob *= 0.92
        elif mode == 'CONTACT':
            if strike:
                prob = min(0.96, prob + 0.08)
            else:
                prob *= 0.90

        prob = max(0.01, min(0.99, prob))
        will_swing = self.rng.random() < prob
        return will_swing, round(prob, 3)
