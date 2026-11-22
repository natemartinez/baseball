"""
Tactical pitch intent and target resolution.

``pitch_intent`` answers where the pitcher is trying to go, never what pitch is
thrown. The accepted values are ``STRIKE``, ``CHASE``, and ``WASTE``. An omitted
intent preserves the historical probabilistic ball-intent mix.
"""

import random
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from ..pitcher_info.pitch_objects import PITCH_CATEGORIES
from ...game_engine.geometry.gameday_math import (
    CHASE_BORDER_FT,
    ZONE_TARGET_BOUNDS,
    ZONE_X_MAX,
    ZONE_X_MIN,
    ZONE_Z_BOT,
    ZONE_Z_TOP,
    classify_gameday_zone,
    sample_zone_target,
)


class PitchSelectionError(ValueError):
    """Raised when a pitch selection or intent contract is invalid."""


VALID_PITCH_INTENTS = ('STRIKE', 'CHASE', 'WASTE')

_INNER_ZONES = frozenset(
    name for name in ZONE_TARGET_BOUNDS if not name.startswith('chase-')
)

_UPPER_ZONES = frozenset(('upper-in', 'upper-middle', 'upper-away'))
_LOWER_ZONES = frozenset(('lower-in', 'lower-middle', 'lower-away'))


def _is_four_seam(name: str) -> bool:
    lowered = str(name or '').lower()
    return any(
        token in lowered
        for token in ('four-seam', '4-seam', 'fourseam', '4seam')
    )


def _is_sinker(name: str) -> bool:
    lowered = str(name or '').lower()
    return any(
        token in lowered
        for token in ('sinker', 'two-seam', '2-seam', 'twoseam', '2seam')
    )


def pitch_specific_zone(
    recommended_zone: str,
    pitch_name: str,
    pitcher_hand: str = 'R',
    batter_side: str = 'R',
    last_pitch_name: Optional[str] = None,
    last_target_zone: Optional[str] = None,
) -> str:
    """Shifts a tactical target into the selected pitch's vertical profile.

    Chase zones are left alone so the existing ball-intent mix remains intact.
    Four-seams prefer the upper third; sinkers prefer the lower third and the
    pitcher's arm-side corner. The mapping is deterministic and adds no RNG
    draws.

    When doubling up on the same pitch (pitch_name == last_pitch_name), alternates
    the target corridor so the pitcher does not repeatedly attack the exact same zone.
    """
    zone = str(recommended_zone or '').lower().strip()
    if not zone or zone == 'waste':
        return recommended_zone

    hand = 'L' if str(pitcher_hand or 'R').upper().startswith('L') else 'R'
    batter = 'L' if str(batter_side or 'R').upper().startswith('L') else 'R'

    # Compute base vertical profile zone
    base_zone = zone
    if not zone.startswith('chase-'):
        if _is_four_seam(pitch_name):
            if zone in _UPPER_ZONES:
                base_zone = zone
            elif zone in _LOWER_ZONES:
                side = zone.split('-', 1)[1]
                base_zone = f'upper-{side}'
            elif zone == 'middle-in':
                base_zone = 'upper-in'
            elif zone == 'middle-away':
                base_zone = 'upper-away'
            elif zone == 'heart':
                base_zone = 'upper-middle'
            else:
                base_zone = 'upper-in' if batter == 'R' else 'upper-away'

        elif _is_sinker(pitch_name):
            if zone in _LOWER_ZONES:
                base_zone = zone
            elif zone in _UPPER_ZONES:
                side = zone.split('-', 1)[1]
                base_zone = f'lower-{side}'
            elif zone == 'heart':
                base_zone = 'lower-middle'
            elif zone == 'middle-in' or zone == 'middle-away':
                base_zone = 'lower-in' if hand == 'R' else 'lower-away'
            else:
                base_zone = 'lower-in' if hand == 'R' else 'lower-away'

    # Check for doubling-up alternation
    is_doubled_up = bool(
        last_pitch_name
        and str(last_pitch_name).strip().lower() == str(pitch_name).strip().lower()
        and last_target_zone
    )

    if not is_doubled_up:
        return base_zone

    prev_zone = str(last_target_zone).lower().strip()
    if base_zone != prev_zone:
        return base_zone

    # Apply tactical alternation based on pitch type
    cat = PITCH_CATEGORIES.get(pitch_name, 'Fastball')

    if _is_four_seam(pitch_name) or 'CUTTER' in pitch_name.upper():
        if prev_zone == 'upper-away':
            return 'upper-in'
        elif prev_zone == 'upper-in':
            return 'upper-away'
        elif prev_zone == 'upper-middle':
            return 'upper-in' if batter == 'R' else 'upper-away'
        else:
            return 'upper-away' if prev_zone != 'upper-away' else 'upper-in'

    if _is_sinker(pitch_name):
        if prev_zone == 'lower-away':
            return 'lower-in'
        elif prev_zone == 'lower-in':
            return 'lower-away'
        elif prev_zone == 'lower-middle':
            return 'lower-in' if hand == 'R' else 'lower-away'
        else:
            return 'lower-in'

    if cat == 'Breaking' or any(t in pitch_name.upper() for t in ('SLIDER', 'SWEEPER', 'CURVE')):
        if prev_zone.startswith('chase-'):
            return 'chase-low' if prev_zone == 'chase-away' else 'chase-away'
        elif prev_zone == 'lower-away':
            return 'lower-in' if hand == 'R' else 'middle-away'
        elif prev_zone == 'lower-in':
            return 'lower-away'
        elif prev_zone == 'middle-away':
            return 'lower-away'
        else:
            return 'middle-away'

    if cat == 'OffSpeed' or any(t in pitch_name.upper() for t in ('CHANGEUP', 'SPLITTER')):
        if prev_zone.startswith('chase-'):
            return 'chase-low' if prev_zone == 'chase-away' else 'chase-away'
        elif prev_zone == 'lower-away':
            return 'lower-middle'
        elif prev_zone == 'lower-middle':
            return 'lower-away'
        else:
            return 'lower-middle'

    return base_zone


@dataclass(frozen=True)
class TargetIntent:
    """Resolved tactical target for one pitch delivery."""

    nominal_zone: str
    target_x: float
    target_z: float
    intended_zone_cat: str
    is_manual_override: bool


def _rand_callable(rng=None) -> Callable[[], float]:
    if rng is None:
        return random.random
    if hasattr(rng, 'random'):
        return rng.random
    return rng


def normalize_pitch_intent(value: Optional[str]) -> Optional[str]:
    """Normalizes a tactical pitch intent (case-insensitive) or raises."""
    if value is None or value == '':
        return None
    if not isinstance(value, str):
        raise PitchSelectionError(
            'pitch_intent must be one of STRIKE, CHASE, or WASTE'
        )
    normalized = value.strip().upper()
    if not normalized:
        return None
    if normalized not in VALID_PITCH_INTENTS:
        raise PitchSelectionError(
            'pitch_intent must be one of STRIKE, CHASE, or WASTE'
        )
    return normalized


def mix_ball_intent(
    recommended_zone: str,
    balls: int,
    strikes: int,
    rng=None,
) -> str:
    """
    Occasionally aim off the plate in early and leverage counts. Without this
    mix a high-command pitcher only targets the rulebook rectangle, making
    walks effectively impossible. The recommended strike target remains the
    default; a chase target is selected on a realistic minority of pitches.

    The RNG sequence is preserved from the original implementation: one draw
    decides whether to chase and a second chooses low vs. away.
    """
    rand = _rand_callable(rng)

    waste_chance = 0.0
    if strikes == 2 and balls >= 2:
        waste_chance = 0.50
    elif balls == 3 and strikes == 0:
        waste_chance = 0.40
    elif balls == 3 and strikes == 1:
        waste_chance = 0.45
    elif balls == 2:
        waste_chance = 0.52
    elif balls == 0 and strikes == 0:
        # Real first-pitch strike rate is far below the command model's
        # default, so mix in a deliberate ball a realistic share of the time.
        waste_chance = 0.38
    elif balls == 0 and strikes == 1:
        waste_chance = 0.45
    elif balls == 1 and strikes == 0:
        waste_chance = 0.45
    elif balls == 1 and strikes == 1:
        waste_chance = 0.38

    if waste_chance > 0.0 and rand() < waste_chance:
        return 'chase-low' if rand() < 0.35 else 'chase-away'
    return recommended_zone


def _sample_chase_target(rng) -> Tuple[str, float, float, str]:
    rand = _rand_callable(rng)
    zone = 'chase-low' if rand() < 0.35 else 'chase-away'
    x, z, category = sample_zone_target(zone, rng=rand)
    return zone, x, z, category


def sample_waste_target(rng=None) -> Tuple[float, float, str]:
    """
    Samples a point at least half a chase width beyond the chase band on one
    side, guaranteeing ``classify_gameday_zone`` returns ``WASTE``. The
    canonical 13-zone display map is left untouched.
    """
    rand = _rand_callable(rng)
    margin = CHASE_BORDER_FT * (0.5 + 0.5 * rand())
    side = int(rand() * 4) % 4

    if side == 0:
        x = ZONE_X_MIN - CHASE_BORDER_FT - margin
        z = ZONE_Z_BOT + (ZONE_Z_TOP - ZONE_Z_BOT) * rand()
    elif side == 1:
        x = ZONE_X_MAX + CHASE_BORDER_FT + margin
        z = ZONE_Z_BOT + (ZONE_Z_TOP - ZONE_Z_BOT) * rand()
    elif side == 2:
        x = ZONE_X_MIN + (ZONE_X_MAX - ZONE_X_MIN) * rand()
        z = ZONE_Z_BOT - CHASE_BORDER_FT - margin
    else:
        x = ZONE_X_MIN + (ZONE_X_MAX - ZONE_X_MIN) * rand()
        z = ZONE_Z_TOP + CHASE_BORDER_FT + margin

    return x, z, classify_gameday_zone(x, z)


def resolve_target_intent(
    recommended_zone: str,
    balls: int,
    strikes: int,
    pitch_intent: Optional[str] = None,
    target_zone: Optional[str] = None,
    custom_target: Optional[Dict[str, float]] = None,
    rng=None,
) -> TargetIntent:
    """
    Resolves the target coordinates for one pitch.

    Precedence:
    1. custom target
    2. explicit ``target_zone``
    3. explicit tactical ``pitch_intent``
    4. recommended zone plus the probabilistic ball-intent mix
    """
    rand = _rand_callable(rng)
    normalized_intent = normalize_pitch_intent(pitch_intent)

    has_exact_target = bool(
        custom_target and 'x' in custom_target and 'z' in custom_target
    )

    if has_exact_target:
        target_x = float(custom_target['x'])
        target_z = float(custom_target['z'])
        return TargetIntent(
            nominal_zone=target_zone or recommended_zone,
            target_x=target_x,
            target_z=target_z,
            intended_zone_cat=classify_gameday_zone(target_x, target_z),
            is_manual_override=True,
        )

    if target_zone:
        target_x, target_z, category = sample_zone_target(target_zone, rng=rand)
        return TargetIntent(
            nominal_zone=target_zone,
            target_x=target_x,
            target_z=target_z,
            intended_zone_cat=category,
            is_manual_override=False,
        )

    if normalized_intent == 'STRIKE':
        zone = recommended_zone if recommended_zone in _INNER_ZONES else 'heart'
        target_x, target_z, category = sample_zone_target(zone, rng=rand)
        return TargetIntent(
            nominal_zone=zone,
            target_x=target_x,
            target_z=target_z,
            intended_zone_cat=category,
            is_manual_override=False,
        )

    if normalized_intent == 'CHASE':
        zone, target_x, target_z, category = _sample_chase_target(rand)
        return TargetIntent(
            nominal_zone=zone,
            target_x=target_x,
            target_z=target_z,
            intended_zone_cat=category,
            is_manual_override=False,
        )

    if normalized_intent == 'WASTE':
        target_x, target_z, category = sample_waste_target(rand)
        return TargetIntent(
            nominal_zone='waste',
            target_x=target_x,
            target_z=target_z,
            intended_zone_cat=category,
            is_manual_override=False,
        )

    zone = mix_ball_intent(recommended_zone, balls, strikes, rng=rand)
    target_x, target_z, category = sample_zone_target(zone, rng=rand)
    return TargetIntent(
        nominal_zone=zone,
        target_x=target_x,
        target_z=target_z,
        intended_zone_cat=category,
        is_manual_override=False,
    )
