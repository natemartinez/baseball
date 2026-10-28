import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from backend.api.app import create_app
from test_ball_flight import _game


EXACT_TARGET = {'x': 0.0, 'z': 2.5}


def test_practice_freezes_the_drill_state_and_repeats_exact_delivery():
    game = _game(seed=2026, batter_id=4)
    game.start_practice()

    first = game.practice_throw_pitch(
        'Spin Monster Sweeper', target_zone='heart', custom_target=dict(EXACT_TARGET)
    )
    first_details = first['pitch_details']
    first_packet = first_details['gameday_packet']
    resolved = game.practice_resolve_pitch(batter_decision='TAKE')
    state = resolved['game_state']

    assert state['balls'] == 0
    assert state['strikes'] == 0
    assert state['outs'] == 0
    assert state['bases'] == {'first': None, 'second': None, 'third': None}
    assert state['current_batter']['name'] == 'Gleyber Torres'
    assert resolved['pitch_details']['pitch_result'] == 'CALLED_STRIKE'

    second = game.practice_throw_pitch(
        'Spin Monster Sweeper', target_zone='heart', custom_target=dict(EXACT_TARGET)
    )
    second_details = second['pitch_details']
    second_packet = second_details['gameday_packet']

    assert second_details['pitch_name'] == 'Spin Monster Sweeper'
    assert second_details['velocity_mph'] == first_details['velocity_mph']
    assert second_packet['intent']['targetX'] == 0.0
    assert second_packet['intent']['targetZ'] == 2.5
    assert second_packet['execution']['realizedX'] == 0.0
    assert second_packet['execution']['realizedZ'] == 2.5
    assert second_packet['execution']['radialMissInches'] == 0.0
    assert second_packet['strategy']['selectedPitch'] == 'Spin Monster Sweeper'
    assert second_packet['strategy']['dynamicModifier'] == 1.0
    assert first_packet['execution']['realizedX'] == second_packet['execution']['realizedX']
    assert first_packet['execution']['realizedZ'] == second_packet['execution']['realizedZ']


def test_practice_end_restores_the_real_game_exactly():
    game = _game(seed=2026, batter_id=4)
    # Advance the real game before practicing.
    game.pitch()
    real = game.get_game_state_payload()

    game.start_practice()
    game.practice_throw_pitch(
        'Power Sinker', target_zone='lower-away', custom_target={'x': 0.4, 'z': 1.9}
    )
    game.practice_resolve_pitch(batter_decision='TAKE')
    game.practice_throw_pitch(
        'Power Sinker', target_zone='lower-away', custom_target={'x': 0.4, 'z': 1.9}
    )
    game.practice_resolve_pitch(batter_decision='TAKE')
    restored = game.end_practice()

    assert restored['balls'] == real['balls']
    assert restored['strikes'] == real['strikes']
    assert restored['outs'] == real['outs']
    assert restored['score'] == real['score']
    assert restored['bases'] == real['bases']
    assert restored['current_batter']['name'] == real['current_batter']['name']
    assert restored['current_batter']['stats'] == real['current_batter']['stats']
    assert restored['current_pitcher']['stats'] == real['current_pitcher']['stats']


def test_normal_pitch_endpoints_are_guarded_during_practice():
    game = _game(seed=2026, batter_id=4)
    game.start_practice()
    blocked = game.throw_pitch(pitch_intent='STRIKE', target_zone='heart')
    assert blocked['status'] == 'error'
    assert 'practice' in blocked['message'].lower()


def test_practice_requires_a_pitch_and_exact_target():
    game = _game(seed=2026, batter_id=4)
    game.start_practice()
    assert game.practice_throw_pitch('', target_zone='heart', custom_target=EXACT_TARGET)['status'] == 'error'
    assert game.practice_throw_pitch('Spin Monster Sweeper', target_zone='heart', custom_target=None)['status'] == 'error'


def test_practice_api_contract():
    client = create_app().test_client()
    assert client.post('/api/start_game', json={'seed': 2026}).status_code == 200
    real = client.get('/api/state').get_json()['game']

    started = client.post('/api/practice/start', json={})
    assert started.status_code == 200
    started_body = started.get_json()
    assert started_body['game']['balls'] == 0
    assert started_body['game']['strikes'] == 0
    assert started_body['lineups']
    assert started_body['rotations']

    thrown = client.post(
        '/api/practice/pitch/throw',
        json={
            'pitch_type': 'Four-Seam Fastball',
            'target_zone': 'heart',
            'target_x': 0.0,
            'target_z': 2.5,
        },
    )
    assert thrown.status_code == 200
    thrown_body = thrown.get_json()
    details = thrown_body['pitch_details']
    assert details['pitch_name'] == 'Four-Seam Fastball'
    assert details['gameday_packet']['execution']['realizedX'] == 0.0
    assert details['gameday_packet']['execution']['realizedZ'] == 2.5
    assert details['gameday_packet']['result']['call'] is None

    resolved = client.post('/api/practice/pitch/resolve', json={'batter_decision': 'TAKE'})
    assert resolved.status_code == 200
    resolved_body = resolved.get_json()
    assert resolved_body['game_state']['balls'] == 0
    assert resolved_body['game_state']['strikes'] == 0
    assert resolved_body['game_state']['current_batter']['name'] == real['current_batter']['name']

    blocked = client.post(
        '/api/pitch/throw',
        json={'pitch_intent': 'STRIKE', 'target_zone': 'heart'},
    )
    assert blocked.status_code == 400

    ended = client.post('/api/practice/end', json={})
    assert ended.status_code == 200
    ended_game = ended.get_json()['game']
    assert ended_game['current_batter']['name'] == real['current_batter']['name']
    assert ended_game['balls'] == real['balls']
    assert ended_game['strikes'] == real['strikes']
    assert ended_game['score'] == real['score']
