#!/usr/bin/env python3
"""
Half-inning team switching regression tests.

The Flask API payload is the client's only source of truth for who is batting
and who is pitching. These tests pin the engine behavior that drives it:
away bats and the home pitcher works the TOP half; home bats and the away
pitcher works the BOTTOM half; the next inning flips back.
"""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.api.app import create_app
from backend.database.db import get_player
from backend.engine.game_engine import GameEngine


def _game(seed=2026):
    home_pitcher = get_player(1)
    away_pitcher = get_player(8)
    home_batter = get_player(2)
    away_batter = get_player(6)
    assert home_pitcher is not None and home_pitcher.is_pitcher
    assert away_pitcher is not None and away_pitcher.is_pitcher
    assert home_batter is not None and not home_batter.is_pitcher
    assert away_batter is not None and not away_batter.is_pitcher

    away = {
        'name': 'Away',
        'position_players': [away_batter],
        'pitchers': {'starters': [away_pitcher], 'bullpen': []},
    }
    home = {
        'name': 'Home',
        'position_players': [home_batter],
        'pitchers': {'starters': [home_pitcher], 'bullpen': []},
    }
    return GameEngine(home, away, 'Home', 'Away', seed=seed)


def _advance_until_half_inning(game, top_bottom, max_at_bats=60):
    for _ in range(max_at_bats):
        if game.top_bottom == top_bottom:
            return
        game.sim_at_bat()
    assert game.top_bottom == top_bottom, (
        f'Half-inning did not reach {top_bottom} within {max_at_bats} at-bats'
    )


def test_half_inning_swaps_batter_and_pitcher_teams():
    game = _game()
    top_state = game.get_game_state_payload()

    assert top_state['inning'] == 1
    assert top_state['top_bottom'] == 'TOP'
    assert top_state['current_batter']['team'] == 'Away'
    assert top_state['current_pitcher']['team'] == 'Home'
    assert top_state['current_pitcher']['id'] == 1

    _advance_until_half_inning(game, 'BOT')
    bottom_state = game.get_game_state_payload()

    assert bottom_state['inning'] == 1
    assert bottom_state['top_bottom'] == 'BOT'
    assert bottom_state['outs'] == 0
    assert bottom_state['balls'] == 0
    assert bottom_state['strikes'] == 0
    assert bottom_state['bases'] == {'first': None, 'second': None, 'third': None}
    assert bottom_state['current_batter']['team'] == 'Home'
    assert bottom_state['current_pitcher']['team'] == 'Away'
    assert bottom_state['current_pitcher']['id'] == 8

    _advance_until_half_inning(game, 'TOP')
    next_top_state = game.get_game_state_payload()

    assert next_top_state['inning'] == 2
    assert next_top_state['top_bottom'] == 'TOP'
    assert next_top_state['current_batter']['team'] == 'Away'
    assert next_top_state['current_pitcher']['team'] == 'Home'
    assert next_top_state['current_pitcher']['id'] == 1


def test_reset_endpoint_accepts_seed_and_returns_full_state():
    client = create_app().test_client()

    first = client.post('/api/reset', json={'seed': 777})
    second = client.post('/api/reset', json={'seed': 777})

    assert first.status_code == 200
    assert second.status_code == 200

    first_payload = first.get_json()
    second_payload = second.get_json()

    assert first_payload['game']['inning'] == 1
    assert first_payload['game']['top_bottom'] == 'TOP'
    assert first_payload['lineups']
    assert first_payload['rotations']
    assert (
        first_payload['game']['current_batter']['id']
        == second_payload['game']['current_batter']['id']
    )
    assert (
        first_payload['game']['current_pitcher']['id']
        == second_payload['game']['current_pitcher']['id']
    )
