#!/usr/bin/env python3
"""
Post-reorganization smoke tests.

Guards the canonical module paths introduced when the engine packages were
split into ``game_engine``, ``pitch_execution``, ``pitch_strategy``, and
``pitcher_info``. Also verifies that the Flask routes used by the Expo client
still respond with the expected payloads.
"""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.api.app import create_app
from backend.engine.game_engine import GameEngine, PitchFlowError
from backend.engine.game_engine.ball_flight import compute_batted_ball_trace
from backend.engine.game_engine.gameday_math import classify_gameday_zone
from backend.engine.game_engine.strike_zone import StrikeZone
from backend.engine.pitching_engine import (
    PITCH_CATEGORIES,
    PitchArsenal,
    PitcherInstanceManager,
    PitchingEngine,
    PitchStrategy,
    calculate_pitch_delivery,
)


def test_canonical_imports_resolve():
    assert GameEngine is not None
    assert PitchFlowError is not None
    assert PitchingEngine is not None
    assert PitchStrategy is not None
    assert PitcherInstanceManager is not None
    assert PitchArsenal is not None
    assert PITCH_CATEGORIES
    assert callable(calculate_pitch_delivery)
    assert callable(compute_batted_ball_trace)
    assert callable(classify_gameday_zone)
    assert StrikeZone is not None

    # Importing the seeder must not raise (do not execute it: it mutates SQLite).
    import backend.database.seed  # noqa: F401


def test_flask_endpoints_smoke():
    client = create_app().test_client()

    health = client.get('/api/health')
    assert health.status_code == 200
    assert health.get_json()['status'] == 'ok'

    state = client.get('/api/state')
    assert state.status_code == 200
    state_data = state.get_json()
    assert state_data['game']
    assert state_data['lineups']
    assert state_data['rotations']

    teams = client.get('/api/teams')
    assert teams.status_code == 200
    team_list = teams.get_json()['teams']
    assert team_list

    roster = client.get(f"/api/rosters?team_id={team_list[0]['id']}")
    assert roster.status_code == 200
    assert roster.get_json()['team_id'] == team_list[0]['id']

    started = client.post(
        '/api/start_game',
        json={
            'home_team_id': team_list[0]['id'],
            'away_team_id': team_list[1]['id'] if len(team_list) > 1 else team_list[0]['id'],
            'seed': 424201,
        },
    )
    assert started.status_code == 200
    started_data = started.get_json()
    assert started_data['top_bottom'] == 'TOP'
    assert started_data['current_pitcher']

    thrown = client.post('/api/pitch/throw', json={})
    assert thrown.status_code == 200
    thrown_data = thrown.get_json()
    assert thrown_data['phase'] == 'THROWN'
    assert thrown_data['pitch_details']
    assert thrown_data['game_state']

    resolved = client.post('/api/pitch/resolve', json={'batter_decision': 'TAKE'})
    assert resolved.status_code == 200
    resolved_data = resolved.get_json()
    assert resolved_data['phase'] == 'RESOLVED'
    assert resolved_data['game_state']

    reset = client.post('/api/reset', json={'seed': 424201})
    assert reset.status_code == 200
    reset_data = reset.get_json()
    assert reset_data['game']
    assert reset_data['lineups']
    assert reset_data['rotations']
