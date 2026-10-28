#!/usr/bin/env python3

import json
import math
import time
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.api.app import create_app
from backend.database.db import get_player
from backend.engine.game_engine import ball_flight
from backend.engine.game_engine.ball_flight import compute_batted_ball_trace
from backend.engine.game_engine import GameEngine


def _game(seed=42, batter_id=4):
    pitcher = get_player(1)
    batter = get_player(batter_id)
    away = {
        'name': 'Away',
        'position_players': [batter],
        'pitchers': {'starters': [pitcher], 'bullpen': []},
    }
    home = {
        'name': 'Home',
        'position_players': [batter],
        'pitchers': {'starters': [pitcher], 'bullpen': []},
    }
    return GameEngine(home, away, 'Home', 'Away', seed=seed)


def _assert_within_pct(actual, expected, pct, label):
    tolerance = abs(expected) * pct
    assert abs(actual - expected) <= tolerance, (
        f'{label}: expected {expected} +/- {tolerance:.2f}, got {actual}'
    )


def test_flight_benchmarks_match_calibration_table():
    cases = [
        (108.0, 28.0, -12.0, 422.0, 4.88, 96.0),
        (105.0, 30.0, 0.0, None, 4.8, None),
        (104.0, 16.0, 14.0, 328.0, 2.82, 38.0),
        (94.0, 36.0, 0.0, None, 5.06, None),
        (76.0, 62.0, 8.0, 178.0, 5.24, 114.0),
        (102.0, 3.0, -18.0, 65.0, None, 3.2),
    ]

    for ev, launch, spray, distance, hang, apex in cases:
        trace = compute_batted_ball_trace(ev, launch, spray)
        assert trace is not None

        if distance is not None:
            _assert_within_pct(trace['distance_ft'], distance, 0.12, 'distance')
        if hang is not None:
            _assert_within_pct(trace['hang_time_s'], hang, 0.10, 'hang time')
        if apex is not None:
            _assert_within_pct(trace['apex_height_ft'], apex, 0.25, 'apex')

    grounder = compute_batted_ball_trace(102.0, 3.0, -18.0)
    assert grounder['hang_time_s'] < 1.0

    trace = compute_batted_ball_trace(105.0, 30.0, 0.0)
    assert 390.0 <= trace['distance_ft'] <= 420.0


def test_spray_sign_and_samples_are_consistent():
    right = compute_batted_ball_trace(100.0, 25.0, 45.0)
    left = compute_batted_ball_trace(100.0, 25.0, -45.0)
    center = compute_batted_ball_trace(100.0, 25.0, 0.0)

    assert right['landing_x_ft'] > 0
    assert right['landing_y_ft'] > 0
    assert left['landing_x_ft'] < 0
    assert left['landing_y_ft'] > 0
    assert abs(center['landing_x_ft']) <= 0.1
    assert center['landing_y_ft'] > 0

    for trace in (right, left, center):
        samples = trace['samples']
        assert len(samples) == trace['sample_count'] == 20
        assert samples[0] == [0.0, 0.0, 3.0]
        assert samples[-1] == [round(trace['landing_x_ft'], 2), round(trace['landing_y_ft'], 2), 0.0]
        assert all(point[2] >= 0.0 for point in samples)

        expected_distance = math.hypot(trace['landing_x_ft'], trace['landing_y_ft'])
        assert abs(trace['distance_ft'] - expected_distance) <= 0.2


def test_degenerate_inputs_do_not_raise():
    for ev, launch, spray in [
        (0.0, -30.0, -80.0),
        (200.0, 85.0, 80.0),
        (-5.0, 0.0, 0.0),
        (100.0, -30.0, 10.0),
        (100.0, 89.0, -80.0),
    ]:
        trace = compute_batted_ball_trace(ev, launch, spray)
        assert trace is not None
        assert len(trace['samples']) == 20
        assert trace['hang_time_s'] > 0

    assert compute_batted_ball_trace(None, 20.0, 0.0) is None
    assert compute_batted_ball_trace(100.0, None, 0.0) is None
    assert compute_batted_ball_trace(100.0, 20.0, None) is None

    ground_contact = compute_batted_ball_trace(
        100.0, 20.0, 0.0, contact_height_ft=0.0
    )
    assert ground_contact['samples'][0] == [0.0, 0.0, 0.0]


def test_solver_is_deterministic_and_fast():
    first = compute_batted_ball_trace(108.0, 28.0, -12.0)
    second = compute_batted_ball_trace(108.0, 28.0, -12.0)
    assert first == second

    started = time.perf_counter()
    for _ in range(5000):
        compute_batted_ball_trace(100.0, 20.0, 5.0)
    elapsed = time.perf_counter() - started
    assert elapsed < 2.0, f'5000 flight solves took {elapsed:.3f}s'


def test_feature_flag_disables_trace(monkeypatch):
    monkeypatch.setattr(ball_flight, 'BALL_FLIGHT_TRACE_ENABLED', False)
    assert compute_batted_ball_trace(108.0, 28.0, -12.0) is None


def test_batted_ball_is_attached_only_to_in_play_results():
    game = _game(seed=2026)
    in_play_seen = False
    non_contact_seen = False

    for _ in range(200):
        if game.game_over:
            break
        result = game.pitch()
        if result.get('status') != 'success':
            break
        pitch = result['pitch_details']
        outcome = pitch.get('pitch_result')
        trace = pitch.get('batted_ball')

        if outcome in ('SINGLE', 'DOUBLE', 'TRIPLE', 'HOME_RUN', 'IN_PLAY_OUT'):
            in_play_seen = True
            assert trace is not None
            assert trace['sample_count'] == 20
            assert trace['samples'][0] == [0.0, 0.0, 3.0]
            assert isinstance(pitch.get('spray_angle_deg'), float)
        elif outcome in ('BALL', 'CALLED_STRIKE', 'SWINGING_STRIKE', 'FOUL'):
            non_contact_seen = True
            assert trace is None

        if in_play_seen and non_contact_seen:
            break

    assert in_play_seen, 'seeded sequence did not produce an in-play ball'
    assert non_contact_seen, 'seeded sequence did not produce a non-contact result'


def test_api_response_includes_batted_ball_for_in_play():
    client = create_app().test_client()
    found = False

    for seed in (4242, 5151, 6060):
        client.post('/api/start_game', json={'seed': seed})
        for _ in range(120):
            response = client.post(
                '/api/pitch',
                json={
                    'pitch_intent': 'STRIKE',
                    'target_zone': 'heart',
                    'batter_approach': 'AUTO',
                },
            )
            if response.status_code != 200:
                break
            body = response.get_json()
            if body.get('status') != 'success':
                break
            pitch = body['pitch_details']
            outcome = pitch.get('pitch_result')
            if outcome in ('SINGLE', 'DOUBLE', 'TRIPLE', 'HOME_RUN', 'IN_PLAY_OUT'):
                trace = pitch.get('batted_ball')
                assert trace is not None
                assert len(trace['samples']) == 20
                assert len(json.dumps(trace)) < 2000
                assert isinstance(pitch.get('spray_angle_deg'), float)
                found = True
                break
        if found:
            break

    assert found, 'API simulation did not produce an in-play batted ball'


def test_trace_flag_does_not_change_seeded_outcomes(monkeypatch):
    def collect():
        game = _game(seed=777)
        rows = []
        for _ in range(12):
            thrown = game.throw_pitch()
            if thrown.get('status') != 'success':
                break
            resolved = game.resolve_pitch()
            if resolved.get('status') != 'success':
                break
            pitch = resolved['pitch_details']
            rows.append(
                (
                    pitch.get('pitch_result'),
                    pitch.get('exit_velocity_mph'),
                    pitch.get('launch_angle_deg'),
                    pitch.get('spray_angle_deg'),
                )
            )
        return rows

    with_trace = collect()
    monkeypatch.setattr(ball_flight, 'BALL_FLIGHT_TRACE_ENABLED', False)
    without_trace = collect()

    assert with_trace == without_trace
    assert any(row[1] is not None for row in with_trace)
