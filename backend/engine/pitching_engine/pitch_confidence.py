"""
Pitcher Confidence & Repertoire Effectiveness Engine.

Models pitch-by-pitch confidence progression, consecutive strike-zone miss degradation,
walk/HBP penalties, hits-allowed collapse, and the holistic ripple effect across a pitcher's
entire arsenal.
"""

from typing import Dict, List, Tuple, Optional


RIPPLE_FACTOR = 0.30
NEUTRAL_CONFIDENCE = 50.0
MAX_CONFIDENCE = 100.0
MIN_CONFIDENCE = 0.0

# Command modification bounds at extreme confidence levels
MAX_CONFIDENCE_PENALTY = 22.0  # At 0% confidence, up to -22 command points
MAX_CONFIDENCE_BOOST = 10.0    # At 100% confidence, up to +10 command points


def calculate_consecutive_miss_penalty(miss_streak: int) -> float:
    """
    Calculates the penalty for failing to locate the strike zone consecutively.
    
    Rule:
    - 1 miss (isolated ball): minor location variance (-2.5%)
    - 2 consecutive misses: stacking begins (-6.0%)
    - 3 consecutive misses: escalates harder (-10.5%)
    - 4 consecutive misses (e.g. four-pitch walk): severe loss (-16.0%)
    - 5+ consecutive misses: continues stacking by -6.5% per additional miss
    """
    if miss_streak <= 0:
        return 0.0
    if miss_streak == 1:
        return -2.5
    if miss_streak == 2:
        return -6.0
    if miss_streak == 3:
        return -10.5
    if miss_streak == 4:
        return -16.0
    return -16.0 - (miss_streak - 4) * 6.5


def calculate_pitch_confidence_delta(
    pitch_result: str,
    consecutive_misses: int = 0,
    is_walk: bool = False,
) -> Tuple[float, int]:
    """
    Evaluates pitch effectiveness and returns (primary_delta, updated_miss_streak).
    
    Uneffective / Ineffective Criteria:
    1. Got hit off of:
       - HOME_RUN: -20.0%
       - TRIPLE: -15.0%
       - DOUBLE: -11.0%
       - SINGLE: -7.0%
    2. Can't locate the strike zone consecutively:
       - Consecutive balls stack increasing penalties starting at >= 2 misses.
    3. Walked / HBP a batter:
       - HIT_BY_PITCH: -9.0%
       - is_walk (e.g. ball 4): additional -6.0% penalty on top of the miss penalty.
       
    Effective Criteria:
    - SWINGING_STRIKE: +6.5%
    - IN_PLAY_OUT: +6.0%
    - CALLED_STRIKE: +4.0%
    - FOUL: +1.5%
    """
    normalized_result = str(pitch_result or '').upper()

    # 1. Got hit off of
    if normalized_result == 'HOME_RUN':
        return -20.0, 0
    if normalized_result == 'TRIPLE':
        return -15.0, 0
    if normalized_result == 'DOUBLE':
        return -11.0, 0
    if normalized_result == 'SINGLE':
        return -7.0, 0

    # 2. Hit by pitch
    if normalized_result == 'HIT_BY_PITCH':
        return -9.0, 0

    # 3. Failed to locate the strike zone (BALL)
    if normalized_result == 'BALL':
        new_streak = consecutive_misses + 1
        delta = calculate_consecutive_miss_penalty(new_streak)
        if is_walk:
            delta -= 6.0  # Additional penalty for issuing a free pass
        return round(delta, 2), new_streak

    # 4. Effective strikes and outs (streak resets to 0)
    if normalized_result == 'SWINGING_STRIKE':
        return +6.5, 0
    if normalized_result == 'IN_PLAY_OUT':
        return +6.0, 0
    if normalized_result == 'CALLED_STRIKE':
        return +4.0, 0
    if normalized_result == 'FOUL':
        return +1.5, 0

    return -1.0, 0


def apply_holistic_confidence_update(
    current_confidences: Dict[str, float],
    all_pitch_names: List[str],
    thrown_pitch_name: str,
    primary_delta: float,
    ripple_factor: float = RIPPLE_FACTOR,
) -> Dict[str, float]:
    """
    Updates the thrown pitch with primary_delta and cascades a holistic ripple
    to all other pitches in the repertoire.
    """
    updated: Dict[str, float] = {}
    ripple_delta = primary_delta * ripple_factor

    # Ensure all repertoire pitches are represented
    names_to_update = set(all_pitch_names)
    names_to_update.add(thrown_pitch_name)
    for k in current_confidences.keys():
        if k != 'overall':
            names_to_update.add(k)

    for name in names_to_update:
        base_val = current_confidences.get(name, NEUTRAL_CONFIDENCE)
        if name == thrown_pitch_name:
            new_val = base_val + primary_delta
        else:
            new_val = base_val + ripple_delta
        
        # Clamp between 0.0 and 100.0
        updated[name] = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, round(new_val, 2)))

    # Compute overall repertoire average
    rep_values = [v for k, v in updated.items() if k != 'overall']
    if rep_values:
        updated['overall'] = round(sum(rep_values) / len(rep_values), 2)

    return updated


def calculate_effective_command_with_confidence(
    base_command: float,
    confidence: float = NEUTRAL_CONFIDENCE,
) -> float:
    """
    Modifies a pitch's command rating according to its confidence total.
    
    - Confidence < 50: Command drops up to MAX_CONFIDENCE_PENALTY (22 pts at 0% confidence).
    - Confidence == 50: Zero modification.
    - Confidence > 50: Command improves up to MAX_CONFIDENCE_BOOST (10 pts at 100% confidence).
    
    Clamped to [30.0, 99.0].
    """
    conf = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, float(confidence)))
    if conf < NEUTRAL_CONFIDENCE:
        # Scale penalty from 0 to -22
        t = (NEUTRAL_CONFIDENCE - conf) / NEUTRAL_CONFIDENCE
        delta = -t * MAX_CONFIDENCE_PENALTY
    else:
        # Scale boost from 0 to +10
        t = (conf - NEUTRAL_CONFIDENCE) / (MAX_CONFIDENCE - NEUTRAL_CONFIDENCE)
        delta = t * MAX_CONFIDENCE_BOOST

    effective = float(base_command) + delta
    return max(30.0, min(99.0, round(effective, 2)))
