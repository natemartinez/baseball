import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from backend.engine.game_engine.engine import GameEngine
from test_ball_flight import _game


def test_engine_has_no_build_gameday_packet():
    engine = _game()
    assert not hasattr(engine, '_build_gameday_packet')


def test_engine_has_no_build_pitch_details():
    engine = _game()
    assert not hasattr(engine, '_build_pitch_details')


def test_engine_has_no_advance_runners_helpers():
    engine = _game()
    assert not hasattr(engine, '_advance_runners_on_hit')
    assert not hasattr(engine, '_advance_runners_on_walk')


def test_engine_has_commit_method():
    engine = _game()
    assert hasattr(engine, '_commit')


def test_engine_has_stats_tracker():
    engine = _game()
    assert hasattr(engine, '_stats_tracker')


def test_full_pitch_cycle_resolves():
    engine = _game(seed=42)
    result = engine.pitch()
    assert result.get('status') == 'success'
