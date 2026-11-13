import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from backend.engine.game_engine.game_logic.inning import HalfInningState, switch_half_inning


def _state(top_bottom='TOP', inning=1):
    return HalfInningState(
        outs=3,
        balls=2,
        strikes=1,
        bases={'first': 'runner', 'second': None, 'third': None},
        top_bottom=top_bottom,
        inning=inning,
        game_over=False,
    )


def test_top_switches_to_bot():
    s = switch_half_inning(_state('TOP', 1), {'Home': 0, 'Away': 0}, 'Home', 'Away')
    assert s.top_bottom == 'BOT'
    assert s.inning == 1


def test_bot_switches_to_top_and_increments_inning():
    s = switch_half_inning(_state('BOT', 1), {'Home': 0, 'Away': 0}, 'Home', 'Away')
    assert s.top_bottom == 'TOP'
    assert s.inning == 2


def test_resets_count_and_bases():
    s = switch_half_inning(_state('TOP', 3), {'Home': 0, 'Away': 0}, 'Home', 'Away')
    assert s.outs == 0 and s.balls == 0 and s.strikes == 0
    assert all(v is None for v in s.bases.values())


def test_game_over_after_9_home_leads():
    s = switch_half_inning(_state('BOT', 9), {'Home': 3, 'Away': 1}, 'Home', 'Away')
    assert s.game_over is True


def test_no_game_over_tied_after_9():
    s = switch_half_inning(_state('BOT', 9), {'Home': 2, 'Away': 2}, 'Home', 'Away')
    assert s.game_over is False


def test_no_game_over_before_9():
    s = switch_half_inning(_state('BOT', 8), {'Home': 5, 'Away': 1}, 'Home', 'Away')
    assert s.game_over is False

