"""
Pitch selection modes, resolved selection model, and the selection resolver.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from ..pitch_execution.pitch_objects import Pitch, PitchArsenal
from .intent import (
    PitchSelectionError,
    TargetIntent,
    normalize_pitch_intent,
    pitch_specific_zone,
    resolve_target_intent,
)
from .strategy import PitchStrategy


class PitchSelectionMode(str, Enum):
    """Who selected the pitch."""

    AI = 'AI'
    USER = 'USER'
    PRACTICE = 'PRACTICE'


@dataclass(frozen=True)
class PitchSelection:
    """The fully resolved pitch choice plus its tactical target."""

    mode: PitchSelectionMode
    source: str
    pitch_name: str
    pitch: Optional[Pitch]
    velocity_mph: float
    spin_rpm: int
    strategy_name: str
    rationale: str
    repertoire_probabilities: Dict[str, float]
    dynamic_modifier: float
    recommended_zone: str
    target_intent: TargetIntent
    pitch_intent: Optional[str] = None


def _value_from_player(player: Any, *keys: str) -> Any:
    if player is None:
        return None
    if isinstance(player, dict):
        for key in keys:
            value = player.get(key)
            if value:
                return value
        vitals = player.get('vitals') or {}
        if isinstance(vitals, dict):
            for key in keys:
                value = vitals.get(key)
                if value:
                    return value
        return None
    for key in keys:
        value = getattr(player, key, None)
        if value:
            return value
    vitals = getattr(player, 'vitals', None)
    if isinstance(vitals, dict):
        for key in keys:
            value = vitals.get(key)
            if value:
                return value
    return None


def _pitcher_hand(strategy: PitchStrategy) -> str:
    raw = _value_from_player(getattr(strategy, 'pitcher', None), 'throws', 'handedness')
    return 'L' if str(raw or 'R').upper().startswith('L') else 'R'


def _batter_side(strategy: PitchStrategy, pitcher_hand: str) -> str:
    raw = _value_from_player(getattr(strategy, 'batter', None), 'handedness', 'bats')
    text = str(raw or 'R').upper()
    if text.startswith('S'):
        return 'L' if pitcher_hand == 'R' else 'R'
    return 'L' if text.startswith('L') else 'R'


def _normalize_mode(mode: Any) -> Optional[PitchSelectionMode]:
    if mode is None or mode == '':
        return None
    if isinstance(mode, PitchSelectionMode):
        return mode
    normalized = str(mode).strip().upper()
    valid = {selection.value for selection in PitchSelectionMode}
    if normalized not in valid:
        raise PitchSelectionError(
            "selection_mode must be 'ai', 'user', or 'practice'"
        )
    return PitchSelectionMode(normalized)


def select_pitch(
    strategy: PitchStrategy,
    arsenal: PitchArsenal,
    balls: int,
    strikes: int,
    situation: str = 'NEUTRAL',
    recent_pitches: Optional[List[str]] = None,
    selection_mode: Optional[str] = None,
    pitch_name: Optional[str] = None,
    pitch_intent: Optional[str] = None,
    target_zone: Optional[str] = None,
    custom_target: Optional[Dict[str, float]] = None,
    practice: bool = False,
    double_play_situation: bool = False,
    rng=None,
) -> PitchSelection:
    """
    Resolves who selects the pitch, the concrete pitch, and the target intent.

    AI selection performs the same weighted draw at the same point in the RNG
    sequence as the historical implementation. User and practice selection
    resolve the requested pitch without drawing a random pitch.
    """
    if practice:
        mode = PitchSelectionMode.PRACTICE
    else:
        mode = _normalize_mode(selection_mode)
        if mode is None:
            mode = PitchSelectionMode.USER if pitch_name else PitchSelectionMode.AI

    if mode is PitchSelectionMode.AI and pitch_name:
        raise PitchSelectionError(
            "selection_mode 'ai' does not accept a pitch_name"
        )
    if mode is not PitchSelectionMode.AI and not pitch_name:
        raise PitchSelectionError(
            "selection_mode 'user' requires a pitch_name"
        )

    normalized_intent = normalize_pitch_intent(pitch_intent)

    if mode is PitchSelectionMode.AI:
        strat_result = strategy.choose_pitch(
            balls=balls,
            strikes=strikes,
            situation=situation,
            recent_pitches=recent_pitches,
            double_play_situation=double_play_situation,
        )
        selected_pitch_name = strat_result['selected_pitch']
        selected_pitch = arsenal.get(selected_pitch_name)
        velocity_mph = float(strat_result['velocity_mph'])
        spin_rpm = int(strat_result['spin_rpm'])
    else:
        selected_pitch = arsenal.get(pitch_name)
        if selected_pitch is None:
            raise PitchSelectionError(f'Unknown pitch: {pitch_name}')
        strat_result = strategy.build_plan(
            balls=balls,
            strikes=strikes,
            situation=situation,
            recent_pitches=recent_pitches,
            double_play_situation=double_play_situation,
        )
        selected_pitch_name = selected_pitch.name
        velocity_mph = float(selected_pitch.velocity_mph)
        spin_rpm = int(selected_pitch.spin_rpm)

    if normalized_intent is None and target_zone is None and not custom_target:
        pitcher_hand = _pitcher_hand(strategy)
        batter_side = _batter_side(strategy, pitcher_hand)
        strat_result = dict(strat_result)
        strat_result['recommended_zone'] = pitch_specific_zone(
            strat_result['recommended_zone'],
            selected_pitch_name,
            pitcher_hand=pitcher_hand,
            batter_side=batter_side,
        )

    target = resolve_target_intent(
        recommended_zone=strat_result['recommended_zone'],
        balls=balls,
        strikes=strikes,
        pitch_intent=normalized_intent,
        target_zone=target_zone,
        custom_target=custom_target,
        practice=mode is PitchSelectionMode.PRACTICE,
        rng=rng,
    )

    return PitchSelection(
        mode=mode,
        source=mode.value,
        pitch_name=selected_pitch_name,
        pitch=selected_pitch,
        velocity_mph=velocity_mph,
        spin_rpm=spin_rpm,
        strategy_name=strat_result['strategy_name'],
        rationale=strat_result['rationale'],
        repertoire_probabilities=dict(strat_result['repertoire_probabilities']),
        dynamic_modifier=float(strat_result['dynamic_modifier']),
        recommended_zone=strat_result['recommended_zone'],
        target_intent=target,
        pitch_intent=normalized_intent,
    )
