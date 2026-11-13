"""
Inning Transition Logic.

Pure functions and dataclasses for half-inning transitions and game-over resolution.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class HalfInningState:
    """State snapshot for the half-inning and count."""

    outs: int
    balls: int
    strikes: int
    bases: Dict[str, Any]
    top_bottom: str
    inning: int
    game_over: bool


def switch_half_inning(
    state: HalfInningState,
    score: Dict[str, int],
    home_name: str,
    away_name: str,
) -> HalfInningState:
    """
    Switches between TOP and BOT half-innings, increments inning on BOT->TOP,
    resets count/bases/outs, and determines game_over condition after 9+ innings.
    """
    new_top_bottom = 'BOT' if state.top_bottom == 'TOP' else 'TOP'
    new_inning = state.inning + (1 if state.top_bottom == 'BOT' else 0)
    game_over = state.game_over

    if state.top_bottom == 'BOT' and new_inning > 9:
        if score.get(home_name, 0) != score.get(away_name, 0):
            game_over = True

    return HalfInningState(
        outs=0,
        balls=0,
        strikes=0,
        bases={'first': None, 'second': None, 'third': None},
        top_bottom=new_top_bottom,
        inning=new_inning,
        game_over=game_over,
    )

