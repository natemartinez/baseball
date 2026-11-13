import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from backend.engine.game_engine.game_logic.count import count_after_pitch


def test_ball_increments():
    assert count_after_pitch(1, 0, 'BALL') == (2, 0)


def test_ball_at_3_resets():
    assert count_after_pitch(3, 1, 'BALL') == (0, 0)


def test_called_strike_increments():
    assert count_after_pitch(0, 1, 'CALLED_STRIKE') == (0, 2)


def test_strikeout_resets():
    assert count_after_pitch(1, 2, 'SWINGING_STRIKE') == (0, 0)


def test_foul_with_two_strikes_caps():
    assert count_after_pitch(2, 2, 'FOUL') == (2, 2)


def test_foul_increments_below_two():
    assert count_after_pitch(0, 0, 'FOUL') == (0, 1)


def test_in_play_resets():
    assert count_after_pitch(2, 1, 'IN_PLAY_OUT') == (0, 0)

