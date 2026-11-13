"""
Game State Mutation Logic.

Computes discrete state diffs (balls, strikes, outs, bases, score) from
resolved BatterActivity without in-place mutation of the engine state machine.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .base_running import advance_on_hit, advance_on_walk
from .batter_stats import BatterStatsTracker


@dataclass
class GameSnapshot:
    """Read-only snapshot of current engine game state."""

    balls: int
    strikes: int
    outs: int
    bases: Dict[str, Any]
    score: Dict[str, int]
    top_bottom: str
    inning: int
    game_over: bool = False


@dataclass
class StateDiff:
    """Discrete state diff describing the effect of a resolved pitch outcome."""

    balls: int
    strikes: int
    outs: int
    bases: Dict[str, Any]
    score_delta: Dict[str, int] = field(default_factory=dict)
    advance_batter: bool = False
    switch_half: bool = False
    game_over: bool = False


def apply_activity(
    snapshot: GameSnapshot,
    activity: Any,
    batter_summary: Dict[str, Any],
    batting_team: str,
    stats_tracker: BatterStatsTracker,
) -> StateDiff:
    """
    Computes a StateDiff from the current game snapshot and resolved batter activity.
    Updates batter box-score stats on stats_tracker.
    """
    balls = snapshot.balls
    strikes = snapshot.strikes
    outs = snapshot.outs
    bases = dict(snapshot.bases)
    score_delta: Dict[str, int] = {}
    advance_batter = False

    stats = stats_tracker.get_line(batter_summary)
    result = str(getattr(activity, 'pitch_result', '') or '').upper()

    if result == 'BALL':
        balls += 1
        if balls == 4:
            bases, runs = advance_on_walk(bases, batter_summary)
            if runs:
                score_delta[batting_team] = score_delta.get(batting_team, 0) + runs
                stats['rbis'] += runs
            balls = 0
            strikes = 0
            advance_batter = True

    elif result in ('CALLED_STRIKE', 'SWINGING_STRIKE'):
        strikes += 1
        if strikes == 3:
            stats['at_bats'] += 1
            outs += 1
            balls = 0
            strikes = 0
            advance_batter = True

    elif result == 'FOUL':
        if strikes < 2:
            strikes += 1

    elif result == 'IN_PLAY_OUT':
        stats['at_bats'] += 1
        outs += 1
        balls = 0
        strikes = 0
        advance_batter = True

    elif result in ('SINGLE', 'DOUBLE', 'TRIPLE', 'HOME_RUN'):
        stats['at_bats'] += 1
        stats['hits'] += 1
        if result == 'HOME_RUN':
            stats['home_runs'] += 1

        bases_taken = {
            'SINGLE': 1,
            'DOUBLE': 2,
            'TRIPLE': 3,
            'HOME_RUN': 4,
        }[result]
        bases, runs = advance_on_hit(bases, bases_taken, batter_summary)
        if runs:
            score_delta[batting_team] = score_delta.get(batting_team, 0) + runs
            stats['rbis'] += runs
        balls = 0
        strikes = 0
        advance_batter = True

    switch_half = outs >= 3

    return StateDiff(
        balls=balls,
        strikes=strikes,
        outs=outs,
        bases=bases,
        score_delta=score_delta,
        advance_batter=advance_batter,
        switch_half=switch_half,
        game_over=snapshot.game_over,
    )

