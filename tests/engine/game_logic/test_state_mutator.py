import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from backend.engine.game_engine.game_logic.state_mutator import (
    GameSnapshot,
    StateDiff,
    apply_activity,
)
from backend.engine.game_engine.game_logic.batter_stats import BatterStatsTracker

EMPTY_BASES = {'first': None, 'second': None, 'third': None}
BATTER_SUM = {'id': 1, 'name': 'Doe', 'jersey_number': 7, 'position': 'RF', 'team': 'Away'}


def _snap(**kwargs):
    defaults = dict(
        balls=0,
        strikes=0,
        outs=0,
        bases=EMPTY_BASES,
        score={'Home': 0, 'Away': 0},
        top_bottom='TOP',
        inning=1,
        game_over=False,
    )
    defaults.update(kwargs)
    return GameSnapshot(**defaults)


def _activity(result):
    a = MagicMock()
    a.pitch_result = result
    a.is_strike = result in ('CALLED_STRIKE', 'SWINGING_STRIKE')
    a.spray_angle_deg = None
    a.batted_ball = None
    return a


def test_ball_increments_balls():
    diff = apply_activity(
        _snap(balls=1), _activity('BALL'), BATTER_SUM, 'Away', BatterStatsTracker()
    )
    assert diff.balls == 2


def test_walk_scores_no_runs_empty_bases():
    diff = apply_activity(
        _snap(balls=3), _activity('BALL'), BATTER_SUM, 'Away', BatterStatsTracker()
    )
    assert diff.advance_batter is True
    assert diff.score_delta.get('Away', 0) == 0


def test_strikeout_advances_batter_adds_out():
    diff = apply_activity(
        _snap(strikes=2), _activity('CALLED_STRIKE'), BATTER_SUM, 'Away', BatterStatsTracker()
    )
    assert diff.outs == 1
    assert diff.advance_batter is True


def test_three_outs_flags_switch_half():
    diff = apply_activity(
        _snap(outs=2), _activity('IN_PLAY_OUT'), BATTER_SUM, 'Away', BatterStatsTracker()
    )
    assert diff.switch_half is True


def test_home_run_scores_one_empty_bases():
    diff = apply_activity(
        _snap(), _activity('HOME_RUN'), BATTER_SUM, 'Away', BatterStatsTracker()
    )
    assert diff.score_delta.get('Away', 0) == 1

