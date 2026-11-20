#!/usr/bin/env python3
"""
End-to-End Statcast Realignment Validation Suite.
Tests API health, game initialization, multi-pitch 2D Gaussian Statcast simulation,
and full at-bat simulation over REST test client.
"""

from pathlib import Path
import sys

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.api.app import create_app


def get_test_client():
    app = create_app()
    return app.test_client()


def test_statcast_health():
    """1. Health Check Endpoint."""
    client = get_test_client()
    res = client.get('/api/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data.get('status') == 'ok'


def test_root_is_api_only():
    """The backend root no longer serves the legacy HTML page."""
    client = get_test_client()
    res = client.get('/')
    assert res.status_code == 200
    assert res.is_json
    assert 'text/html' not in res.content_type
    assert res.get_json()['service'] == 'baseball-simulation-api'


def test_statcast_initial_state():
    """2. Initial State Endpoint."""
    client = get_test_client()
    res = client.get('/api/state')
    assert res.status_code == 200
    state = res.get_json()
    assert len(state['teams']) == 2
    assert len(state['lineups']) == 2
    assert len(state['rotations']) == 2


def test_statcast_multi_pitch_simulation():
    """3 & 4. Start Game & 100-Pitch 2D Gaussian Simulation."""
    client = get_test_client()
    res = client.post('/api/start_game', json={'home_team_id': 1, 'away_team_id': 2})
    assert res.status_code == 200

    strikes_count = 0
    balls_count = 0
    leaks_count = 0
    shadow_hits = 0
    miss_radii = []
    max_radius_seen = 0.0

    for i in range(100):
        target_zone = "lower-away" if i % 2 == 0 else "heart"
        r = client.post('/api/pitch', json={
            'pitch_intent': 'STRIKE',
            'target_zone': target_zone,
            'batter_approach': 'AUTO'
        })
        assert r.status_code == 200
        pkt = r.get_json()['pitch_details']['gameday_packet']

        is_strike = pkt['result']['isStrike']
        if is_strike:
            strikes_count += 1
        else:
            balls_count += 1

        if pkt['execution']['isHeartZoneLeak']:
            leaks_count += 1
        if pkt['execution']['hitShadowZoneTarget']:
            shadow_hits += 1

        miss_radii.append(pkt['execution']['radialMissInches'])
        from backend.engine.game_engine.gameday_math import get_max_error_radius_inches
        max_radius_seen = max(
            max_radius_seen,
            pkt['execution'].get(
                'maxRadiusInches',
                get_max_error_radius_inches(pkt['meta']['commandRating']),
            ),
        )

    mean_miss = round(sum(miss_radii) / len(miss_radii), 2)
    assert len(miss_radii) == 100

    # Truncated spray cloud: every miss is bounded by the largest radius used
    # across the 100 deliveries (command/leverage changes per pitch).
    assert 0.05 <= mean_miss <= max_radius_seen + 0.1
    assert max(miss_radii) <= max_radius_seen + 0.2


def test_statcast_sim_at_bat():
    """5. Sim At-Bat Endpoint."""
    client = get_test_client()
    client.post('/api/start_game', json={'home_team_id': 1, 'away_team_id': 2})
    res = client.post('/api/sim_at_bat')
    assert res.status_code == 200
    ab_res = res.get_json()
    assert 'pitch_details' in ab_res
    assert 'game_state' in ab_res


def test_game_engine_exposes_last_pitch_context_black_box():
    from backend.engine.game_engine.engine import GameEngine
    from backend.api.routes import load_team_roster

    home_roster = load_team_roster(1)
    away_roster = load_team_roster(2)
    game_engine = GameEngine(home_roster, away_roster)

    thrown = game_engine.throw_pitch(pitch_name="4-Seam Fastball")
    assert thrown["status"] == "success"
    assert game_engine.last_pitch_context is not None
    assert game_engine.last_pitch_context.delivery["selected_pitch"] == thrown["pitch_details"]["pitch_name"]
    assert game_engine.last_pitch_context.gameday_packet == thrown["gameday_packet"]

    resolved = game_engine.resolve_pitch()
    assert resolved["status"] == "success"
    assert game_engine.last_pitch_context.activity is not None
    assert game_engine.last_pitch_context.gameday_packet == resolved["gameday_packet"]


