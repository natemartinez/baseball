"""
Count State Machine.

Pure state-transition functions for pitch count updates (balls, strikes).
"""

from typing import Tuple


def count_after_pitch(
    balls: int, strikes: int, pitch_result: str
) -> Tuple[int, int]:
    """
    Computes the resulting (balls, strikes) after a pitch outcome.
    Resets to (0, 0) upon a walk (4 balls), strikeout (3 strikes), or ball put in play.
    Caps fouls at 2 strikes.
    """
    result = str(pitch_result or '').upper()
    if result == 'BALL':
        if balls >= 3:
            return 0, 0
        return balls + 1, strikes
    if result in ('CALLED_STRIKE', 'SWINGING_STRIKE'):
        if strikes >= 2:
            return 0, 0
        return balls, strikes + 1
    if result == 'FOUL':
        return balls, min(2, strikes + 1)
    return 0, 0

