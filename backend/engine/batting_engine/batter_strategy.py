"""
MLB Statcast Batter Swing-Decision Model.

Evaluates whether a batter swings at a realized pitch using an interpretable
log-odds model. Inputs include zone location, count leverage, batter
vision/discipline, hot/cold zone damage, pitch type and quality, pitcher stuff,
the current at-bat pitch sequence, situation, and the selected approach mode.

The model is deterministic given an injected RNG and never mutates game state.
"""

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

from .batters import InGameBatterRatings

_CONFIG_PATH = Path(__file__).with_name('swing_model_config.json')
with _CONFIG_PATH.open(encoding='utf-8') as _config_file:
    MODEL_CONFIG: Dict[str, Any] = json.load(_config_file)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _number(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


@dataclass(frozen=True)
class SwingEvaluation:
    """A single swing/take decision with its log-odds contribution breakdown."""

    will_swing: bool
    probability: float
    base_logit: float
    factors: Dict[str, float]
    zone_class: str
    count_key: str
    model_version: str

    @property
    def logit(self) -> float:
        return self.base_logit + sum(self.factors.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'model_version': self.model_version,
            'will_swing': self.will_swing,
            'probability': round(self.probability, 4),
            'base_logit': round(self.base_logit, 4),
            'logit': round(self.logit, 4),
            'zone_class': self.zone_class,
            'count_key': self.count_key,
            'factors': {
                key: round(value, 4) for key, value in self.factors.items()
            },
        }


class BatterStrategy:
    """Decides swing vs. take for a single pitch."""

    def __init__(self, ratings: Any, rng: Optional[random.Random] = None):
        if isinstance(ratings, InGameBatterRatings):
            self.ratings = ratings
        else:
            from .batters import BatterInstanceManager

            self.ratings = BatterInstanceManager.get_adjusted_ratings(ratings)
        self.rng = rng or random

    @staticmethod
    def _zone_class(zone_category: str, is_strike: bool) -> str:
        category = str(zone_category or 'SHADOW').upper()
        if category == 'HEART':
            return 'heart'
        if category == 'SHADOW':
            return 'shadow_strike' if is_strike else 'shadow_ball'
        if category == 'CHASE':
            return 'chase'
        return 'waste'

    @staticmethod
    def _count_key(balls: int, strikes: int) -> str:
        return f'{int(balls)}-{int(strikes)}'

    def _normalize_pitch(
        self,
        delivery: Any,
        actual_zone_name: Optional[str],
        is_strike: Optional[bool],
    ) -> Dict[str, Any]:
        if isinstance(delivery, dict):
            pitch = delivery
            zone_category = str(pitch.get('realized_zone_cat', 'SHADOW')).upper()
            strike = bool(pitch.get('is_strike', False)) if is_strike is None else bool(is_strike)
            zone_name = (
                actual_zone_name
                or pitch.get('nominal_zone')
                or pitch.get('actual_zone')
                or 'heart'
            )
            return {
                'pitch': pitch,
                'zone_category': zone_category,
                'zone_name': str(zone_name),
                'is_strike': strike,
                'velocity': _number(pitch.get('velocity_mph'), 93.0),
                'pitch_category': str(pitch.get('pitch_category', 'Fastball')),
                'horizontal_break': abs(_number(pitch.get('horizontal_break_in'), 0.0)),
                'vertical_break': abs(
                    _number(pitch.get('induced_vertical_break_in'), 0.0)
                ),
                'pitcher_ratings': pitch.get('adjusted_ratings') or {},
            }

        # Legacy positional form: delivery is the zone category string.
        return {
            'pitch': {},
            'zone_category': str(delivery or 'SHADOW').upper(),
            'zone_name': str(actual_zone_name or 'heart'),
            'is_strike': bool(is_strike),
            'velocity': 93.0,
            'pitch_category': 'Fastball',
            'horizontal_break': 0.0,
            'vertical_break': 0.0,
            'pitcher_ratings': {},
        }

    def evaluate_swing(
        self,
        delivery: Any,
        actual_zone_name: Optional[str] = None,
        is_strike: Optional[bool] = None,
        balls: int = 0,
        strikes: int = 0,
        approach_mode: str = 'AUTO',
        *,
        pitch_sequence: Optional[Sequence[Dict[str, Any]]] = None,
        outs: int = 0,
        runners: Sequence[bool] = (False, False, False),
        score_diff: int = 0,
        inning: int = 1,
        pitcher_ratings: Optional[Dict[str, Any]] = None,
    ) -> SwingEvaluation:
        """Evaluates a pitch and returns the probability plus its factors."""
        info = self._normalize_pitch(delivery, actual_zone_name, is_strike)
        zone_class = self._zone_class(info['zone_category'], info['is_strike'])
        count_key = self._count_key(balls, strikes)
        strike = info['is_strike']
        sequence = list(pitch_sequence or [])

        config = MODEL_CONFIG
        base_logit = float(config['zone_logit'][zone_class])
        factors: Dict[str, float] = {}

        if count_key == '3-0':
            count_factor = float(
                config['three_ball_no_strike'][zone_class]
            ) - base_logit
        elif strikes == 2:
            count_factor = float(config['two_strike']['general'])
        else:
            count_factor = float(config['count_logit'].get(count_key, 0.0))
        factors['count'] = count_factor

        two_strike_factor = 0.0
        if strikes == 2:
            if zone_class in ('heart', 'shadow_strike'):
                two_strike_factor = float(config['two_strike']['in_zone'])
            elif zone_class == 'shadow_ball':
                two_strike_factor = float(config['two_strike']['shadow_ball'])
            elif zone_class == 'chase':
                two_strike_factor = float(config['two_strike']['chase'])
            else:
                two_strike_factor = float(config['two_strike']['waste'])
        factors['two_strike'] = two_strike_factor

        discipline_cfg = config['discipline']
        discipline_z = _clamp(
            (_number(getattr(self.ratings, 'vision', 60.0), 60.0)
             - float(discipline_cfg['center'])) / float(discipline_cfg['scale']),
            -float(discipline_cfg['clamp']),
            float(discipline_cfg['clamp']),
        )
        factors['discipline'] = (
            float(discipline_cfg['strike']) if strike else float(discipline_cfg['ball'])
        ) * discipline_z

        hot_cold_cfg = config['hot_cold']
        slugging = _number(
            self.ratings.hot_zones.get(info['zone_name'], hot_cold_cfg['center']),
            float(hot_cold_cfg['center']),
        )
        hot_cold_z = _clamp(
            (slugging - float(hot_cold_cfg['center'])) / float(hot_cold_cfg['scale']),
            -float(hot_cold_cfg['clamp']),
            float(hot_cold_cfg['clamp']),
        )
        factors['hot_cold'] = (
            float(hot_cold_cfg['strike']) if strike else float(hot_cold_cfg['ball'])
        ) * hot_cold_z

        category = info['pitch_category']
        pitch_type_cfg = config['pitch_type'].get(
            category, config['pitch_type']['Fastball']
        )
        factors['pitch_type'] = (
            float(pitch_type_cfg['strike']) if strike else float(pitch_type_cfg['ball'])
        )
        if strikes == 2 and not strike:
            factors['pitch_type'] += float(pitch_type_cfg['two_strike_ball'])

        velocity_cfg = config['velocity']
        velocity_z = _clamp(
            (info['velocity'] - float(velocity_cfg['center']))
            / float(velocity_cfg['scale']),
            -float(velocity_cfg['clamp']),
            float(velocity_cfg['clamp']),
        )
        factors['velocity'] = (
            float(velocity_cfg['strike']) if strike else float(velocity_cfg['ball'])
        ) * velocity_z

        movement_cfg = config['movement']
        movement = info['horizontal_break'] + info['vertical_break']
        movement_z = _clamp(
            (movement - float(movement_cfg['center'])) / float(movement_cfg['scale']),
            -float(movement_cfg['clamp']),
            float(movement_cfg['clamp']),
        )
        factors['movement'] = (
            float(movement_cfg['strike']) if strike else float(movement_cfg['ball'])
        ) * movement_z

        pitcher_stuff_factor = 0.0
        if not strike and category in ('Breaking', 'OffSpeed'):
            ratings_source = pitcher_ratings or info['pitcher_ratings'] or {}
            effective_break = _number(
                ratings_source.get('effective_break'),
                float(config['pitcher_stuff']['center']),
            )
            stuff_cfg = config['pitcher_stuff']
            stuff_z = _clamp(
                (effective_break - float(stuff_cfg['center']))
                / float(stuff_cfg['scale']),
                -float(stuff_cfg['clamp']),
                float(stuff_cfg['clamp']),
            )
            pitcher_stuff_factor = float(stuff_cfg['ball']) * stuff_z
        factors['pitcher_stuff'] = pitcher_stuff_factor

        sequence_cfg = config['sequence']
        sequence_factor = 0.0
        if sequence:
            last = sequence[-1] or {}
            last_category = str(
                last.get('pitch_category')
                or last.get('pitchCategory')
                or 'Fastball'
            )
            if last_category == category:
                entry = sequence_cfg['same_type']
                sequence_factor += float(entry['strike'] if strike else entry['ball'])

            prior_breaking = sum(
                1
                for pitch in sequence
                if str(pitch.get('pitch_category') or pitch.get('pitchCategory'))
                == 'Breaking'
            )
            if category in ('Breaking', 'OffSpeed') and prior_breaking:
                entry = sequence_cfg['prior_breaking']
                capped = min(prior_breaking, int(entry['max_count']))
                sequence_factor += capped * float(
                    entry['strike'] if strike else entry['ball']
                )

            consecutive = 0
            for pitch in reversed(sequence):
                pitch_category = str(
                    pitch.get('pitch_category')
                    or pitch.get('pitchCategory')
                    or 'Fastball'
                )
                if pitch_category != category:
                    break
                consecutive += 1
            if consecutive >= 2:
                entry = sequence_cfg['consecutive_same_type']
                sequence_factor += float(
                    entry['strike'] if strike else entry['ball']
                )

            last_result = str(last.get('result') or '').upper()
            result_entry = sequence_cfg['last_result'].get(last_result)
            if result_entry:
                sequence_factor += float(
                    result_entry['strike'] if strike else result_entry['ball']
                )
        factors['sequence'] = _clamp(
            sequence_factor,
            -float(sequence_cfg['max_abs']),
            float(sequence_cfg['max_abs']),
        )

        situation_cfg = config['situation']
        situation_factor = 0.0
        runner_list = list(runners or ())
        runner_on_third = bool(runner_list[2]) if len(runner_list) > 2 else False
        if runner_on_third and outs < 2:
            entry = situation_cfg['runner_on_third_lt2']
            situation_factor += float(entry['strike'] if strike else entry['ball'])
        if int(outs) == 2:
            entry = situation_cfg['two_outs']
            situation_factor += float(entry['strike'] if strike else entry['ball'])
        diff = abs(int(score_diff or 0))
        if diff <= 2 and int(inning) >= 7:
            entry = situation_cfg['close_late']
            situation_factor += float(entry['strike'] if strike else entry['ball'])
        if diff >= 5:
            entry = situation_cfg['blowout']
            situation_factor += float(entry['strike'] if strike else entry['ball'])
        factors['situation'] = _clamp(
            situation_factor,
            -float(situation_cfg['max_abs']),
            float(situation_cfg['max_abs']),
        )

        approach_cfg = config['approach']
        mode = str(approach_mode or 'AUTO').upper()
        entry = approach_cfg.get(mode, approach_cfg['AUTO'])
        approach_factor = float(entry['overall']) + float(
            entry['strike'] if strike else entry['ball']
        )
        if zone_class == 'waste':
            approach_factor += float(entry['waste'])
        factors['approach'] = _clamp(
            approach_factor,
            -float(approach_cfg['max_abs']),
            float(approach_cfg['max_abs']),
        )

        logit = base_logit + sum(factors.values())
        probability = _clamp(
            _sigmoid(logit),
            float(config['bounds']['min_probability']),
            float(config['bounds']['max_probability']),
        )
        will_swing = self.rng.random() < probability

        return SwingEvaluation(
            will_swing=will_swing,
            probability=probability,
            base_logit=base_logit,
            factors=factors,
            zone_class=zone_class,
            count_key=count_key,
            model_version=str(config['model_version']),
        )

    def decide_swing(
        self,
        delivery: Any,
        actual_zone_name: Optional[str] = None,
        is_strike: Optional[bool] = None,
        balls: int = 0,
        strikes: int = 0,
        approach_mode: str = 'AUTO',
        **kwargs: Any,
    ) -> Tuple[bool, float]:
        """
        Returns (will_swing, swing_probability).

        Accepts either a pitch-delivery dict from the PitchingEngine or the
        legacy positional form (zone_category, zone_name, is_strike, balls,
        strikes). Modern callers should pass the extended context as keywords.
        """
        evaluation = self.evaluate_swing(
            delivery,
            actual_zone_name=actual_zone_name,
            is_strike=is_strike,
            balls=balls,
            strikes=strikes,
            approach_mode=approach_mode,
            **kwargs,
        )
        return evaluation.will_swing, round(evaluation.probability, 3)
