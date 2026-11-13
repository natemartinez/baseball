import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from backend.engine.game_engine.serialization.state_payload import build_state_payload


def _mock_engine():
    e = MagicMock()
    e.inning = 3
    e.top_bottom = 'TOP'
    e.outs = 1
    e.balls = 2
    e.strikes = 0
    e.score = {'Home': 2, 'Away': 1}
    e.bases = {'first': None, 'second': None, 'third': None}
    e.game_over = False
    e.home_name = 'Home'
    e.away_name = 'Away'
    e.pitch_count_home = 42
    e.pitch_count_away = 38
    e.current_batter_obj.return_value = None
    e.current_pitcher_obj.return_value = None
    e.current_pitcher_state.return_value = None
    e._batter_game_stats = {}
    return e


def test_returns_required_keys():
    payload = build_state_payload(_mock_engine())
    for key in (
        'inning',
        'top_bottom',
        'outs',
        'balls',
        'strikes',
        'score',
        'bases',
        'current_batter',
        'current_pitcher',
        'game_over',
    ):
        assert key in payload, f"Missing key: {key}"


def test_score_shape():
    payload = build_state_payload(_mock_engine())
    assert payload['score'] == {'home': 2, 'away': 1}

