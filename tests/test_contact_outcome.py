import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from backend.api.app import create_app
from backend.engine.batting_engine.contact_outcome import (
    fielder_for_landing,
    resolve_contact_outcome,
)
from test_ball_flight import _game


def test_contact_outcome_maps_landing_to_result():
    home_run = resolve_contact_outcome(110, 30, 0)
    assert home_run['call'] == 'HOME_RUN'
    assert home_run['is_in_play'] is True
    assert home_run['batted_ball'] is not None

    # 324 ft to center field lands 6 ft from the CF's standard spot.
    caught = resolve_contact_outcome(100, 20, 0)
    assert caught['call'] == 'IN_PLAY_OUT'
    assert caught['fielder_name'] == 'CF'
    assert caught['batted_ball'] is not None

    # 297 ft into the right-field gap lands outside all fielder radii.
    gap = resolve_contact_outcome(95, 20, 40)
    assert gap['call'] == 'DOUBLE'
    assert gap['fielder_name'] is None

    weak = resolve_contact_outcome(119.3, -25.0, -33.6)
    assert weak['call'] == 'SINGLE'
    assert weak['fielder_name'] is None
    assert weak['batted_ball'] is not None


def test_short_grounder_in_front_of_plate_is_not_an_automatic_out():
    # The reported bug: this used to be IN_PLAY_OUT with a landing 5 ft in
    # front of home. No fielder is within reach, so it is an infield hit.
    contact = resolve_contact_outcome(119.3, -25.0, -33.6)
    assert contact['call'] == 'SINGLE'
    assert contact['batted_ball']['landing_y_ft'] < 10
    assert contact['fielder_name'] is None


def test_fly_ball_inside_a_fielder_radius_is_an_out():
    center_fly = resolve_contact_outcome(95, 45, 0)
    assert center_fly['call'] == 'IN_PLAY_OUT'
    assert center_fly['fielder_name'] == 'CF'
    assert center_fly['fielder_distance_ft'] is not None
    assert center_fly['fielder_distance_ft'] <= center_fly['fielder_radius_ft']


def test_contact_outcome_foul_has_no_trace():
    foul = resolve_contact_outcome(95, 20, 60)
    assert foul['call'] == 'FOUL'
    assert foul['is_in_play'] is False
    assert foul['batted_ball'] is None


def test_contact_outcome_is_deterministic():
    first = resolve_contact_outcome(104.3, 22.1, -12.5)
    second = resolve_contact_outcome(104.3, 22.1, -12.5)
    assert first == second


def test_contact_outcome_invalid_inputs_return_none():
    assert resolve_contact_outcome(float('nan'), 20, 0) is None
    assert resolve_contact_outcome(None, 20, 0) is None


def test_all_ai_in_play_results_follow_fielder_reach_rule():
    """Every out lands inside a fielder radius; every hit lands outside them."""
    game = _game(seed=2026, batter_id=4)
    outs = []
    hits = 0

    for _ in range(600):
        if game.game_over:
            break
        result = game.pitch()
        if result.get('status') != 'success':
            break

        details = result['pitch_details']
        call = details.get('pitch_result')
        if call not in ('IN_PLAY_OUT', 'SINGLE', 'DOUBLE', 'TRIPLE', 'HOME_RUN'):
            continue

        trace = details.get('batted_ball')
        assert trace is not None
        fielder = fielder_for_landing(
            trace['landing_x_ft'], trace['landing_y_ft']
        )

        if call == 'IN_PLAY_OUT':
            assert fielder is not None, (
                f'Unfielded out at ({trace["landing_x_ft"]}, '
                f'{trace["landing_y_ft"]})'
            )
            outs.append((fielder['id'], trace['landing_y_ft']))
        else:
            # Home runs clear the fence even if their landing point is within
            # a deep outfielder's circle; all other hits must be outside reach.
            if call != 'HOME_RUN':
                assert fielder is None, (
                    f'{call} landed inside {fielder["label"]}\'s radius'
                )
            hits += 1

    assert outs and hits
    # Outs must be spread across the field, not clustered in front of home.
    assert len({fielder_id for fielder_id, _ in outs}) >= 3
    assert max(depth for _, depth in outs) > 150.0


def test_engine_contact_override_and_swing_miss():
    game = _game(seed=2026, batter_id=4)
    assert game.throw_pitch(pitch_intent='STRIKE', target_zone='heart')['status'] == 'success'

    resolved = game.resolve_pitch(
        contact={
            'contacted': True,
            'exit_velocity_mph': 110,
            'launch_angle_deg': 30,
            'spray_angle_deg': 0,
        }
    )
    details = resolved['pitch_details']
    assert details['batter_decision'] == 'SWING'
    assert details['pitch_result'] == 'HOME_RUN'
    assert details['exit_velocity_mph'] == 110.0
    assert details['batted_ball'] is not None

    miss_game = _game(seed=2026, batter_id=4)
    miss_game.throw_pitch(pitch_intent='STRIKE', target_zone='heart')
    missed = miss_game.resolve_pitch(contact={'contacted': False})
    assert missed['pitch_details']['pitch_result'] == 'SWINGING_STRIKE'
    assert missed['pitch_details']['batted_ball'] is None


def test_engine_contact_foul_has_no_trace():
    game = _game(seed=2026, batter_id=4)
    game.throw_pitch(pitch_intent='STRIKE', target_zone='heart')
    resolved = game.resolve_pitch(
        contact={
            'contacted': True,
            'exit_velocity_mph': 95,
            'launch_angle_deg': 20,
            'spray_angle_deg': 60,
        }
    )
    assert resolved['pitch_details']['pitch_result'] == 'FOUL'
    assert resolved['pitch_details']['batted_ball'] is None


def test_take_resolution_is_unchanged_without_contact():
    game = _game(seed=2026, batter_id=4)
    game.throw_pitch(pitch_intent='STRIKE', target_zone='heart')
    resolved = game.resolve_pitch(batter_decision='TAKE')
    details = resolved['pitch_details']
    assert details['batter_decision'] == 'TAKE'
    assert details['pitch_result'] in ('CALLED_STRIKE', 'BALL')


def test_api_resolve_accepts_contact_report():
    client = create_app().test_client()
    client.post('/api/start_game', json={'seed': 2026})
    thrown = client.post(
        '/api/pitch/throw',
        json={'pitch_intent': 'STRIKE', 'target_zone': 'heart'},
    )
    assert thrown.status_code == 200

    response = client.post(
        '/api/pitch/resolve',
        json={
            'batter_decision': 'SWING',
            'contact': {
                'contacted': True,
                'exit_velocity_mph': 110,
                'launch_angle_deg': 30,
                'spray_angle_deg': 0,
            },
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    details = body['pitch_details']
    assert details['pitch_result'] == 'HOME_RUN'
    assert details['batter_decision'] == 'SWING'
    assert details['batted_ball'] is not None


def test_api_invalid_contact_degrades_to_swing_miss():
    client = create_app().test_client()
    client.post('/api/start_game', json={'seed': 2026})
    client.post(
        '/api/pitch/throw',
        json={'pitch_intent': 'STRIKE', 'target_zone': 'heart'},
    )
    response = client.post(
        '/api/pitch/resolve',
        json={'batter_decision': 'SWING', 'contact': {'contacted': True}},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body['pitch_details']['pitch_result'] == 'SWINGING_STRIKE'
