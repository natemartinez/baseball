import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from backend.api.app import create_app
from backend.engine.batting_engine.contact import (
    fielder_for_landing,
    resolve_contact_outcome,
)
from tests.conftest import _game


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
    assert gap['call'] == 'SINGLE'
    assert gap['fielder_name'] is None

    weak = resolve_contact_outcome(119.3, -25.0, -33.6)
    assert weak['call'] == 'SINGLE'
    assert weak['fielder_name'] is None
    assert weak['batted_ball'] is not None


def test_short_grounder_in_front_of_plate_is_not_an_automatic_out():
    # Grounder through the gap rolls past the infielders and is an infield/outfield hit
    contact = resolve_contact_outcome(119.3, -25.0, -33.6)
    assert contact['call'] == 'SINGLE'
    assert contact['batted_ball']['landing_y_ft'] >= 100.0
    assert contact['fielder_name'] is None


def test_routine_grounders_are_fielded_by_infielders():
    # Routine grounder toward SS (-18 deg, 92 mph) reaches SS depth and is an out
    ss_grounder = resolve_contact_outcome(92.0, 2.0, -18.0)
    assert ss_grounder['call'] == 'IN_PLAY_OUT'
    assert ss_grounder['fielder_name'] == 'SS'
    assert 'Ground out to SS' in ss_grounder['description']

    # Routine grounder toward 2B (+18 deg, 92 mph) reaches 2B depth and is an out
    second_grounder = resolve_contact_outcome(92.0, 2.0, 18.0)
    assert second_grounder['call'] == 'IN_PLAY_OUT'
    assert second_grounder['fielder_name'] == '2B'
    assert 'Ground out to 2B' in second_grounder['description']


def test_routine_ground_out_has_realistic_transit_time():
    out_play = resolve_contact_outcome(92.0, 2.0, -18.0)
    assert out_play['call'] == 'IN_PLAY_OUT'
    assert out_play['fielder_name'] == 'SS'
    trace = out_play['batted_ball']
    assert trace is not None
    # 123 ft to SS at 92 MPH should take 0.90s - 1.25s (NOT 4.26s)
    assert 0.90 <= trace['hang_time_s'] <= 1.25
    assert len(trace['samples']) == 20


def test_gap_grounders_roll_into_outfield_for_singles():
    # Scorcher through the gap (-33.6 deg) splits fielders into shallow outfield
    gap_single = resolve_contact_outcome(105.0, 0.0, -33.6)
    assert gap_single['call'] == 'SINGLE'
    assert gap_single['batted_ball']['distance_ft'] >= 160.0


def test_fly_ball_inside_a_fielder_radius_is_an_out():
    center_fly = resolve_contact_outcome(95, 45, 0)
    assert center_fly['call'] == 'IN_PLAY_OUT'
    assert center_fly['fielder_name'] == 'CF'
    assert center_fly['fielder_distance_ft'] is not None
    assert center_fly['fielder_distance_ft'] <= center_fly['fielder_radius_ft']


def test_contact_outcome_foul_has_trace():
    foul = resolve_contact_outcome(95, 20, 60)
    assert foul['call'] == 'FOUL'
    assert foul['is_in_play'] is False
    assert foul['batted_ball'] is not None
    assert len(foul['batted_ball']['samples']) >= 2
    assert foul['batted_ball']['hang_time_s'] > 0


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

        if call == 'IN_PLAY_OUT':
            assert trace.get('fielded') is True, (
                f'Unfielded out at ({trace["landing_x_ft"]}, '
                f'{trace["landing_y_ft"]})'
            )
            outs.append((trace.get('fielder_id'), trace['landing_y_ft']))
        else:
            # Home runs clear the fence even if their landing point is within
            # a deep outfielder's circle; airborne hits must land outside reach.
            # Grounders that pierce the infield are base hits even if they roll
            # to a stop in an outfielder's territory.
            launch_deg = details.get('launch_angle_deg')
            if call != 'HOME_RUN' and (launch_deg is None or launch_deg >= 10.0):
                assert trace.get('fielding_type') not in ('ROUTINE_FLY_CATCH', 'RUNNING_CATCH'), (
                    f'{call} was caught airborne'
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
    assert resolved['pitch_details']['batted_ball'] is not None
    assert len(resolved['pitch_details']['batted_ball']['samples']) >= 2


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


def test_resolve_contact_outcome_emits_enriched_fielding_telemetry():
    res = resolve_contact_outcome(95.0, 20.0, 0.0)
    assert res is not None
    assert "batted_ball" in res
    trace = res["batted_ball"]
    assert "fielded" in trace
    assert "fielder_id" in trace
    assert "fielding_type" in trace
    assert "fielder_start" in trace
    assert "intercept_point" in trace
    assert len(trace["samples"]) == 20
    assert trace["samples"][-1][3] == pytest.approx(trace["hang_time_s"], abs=0.02)


def test_home_run_prescreening_bypasses_fielding():
    # 110 mph at 30 deg to center field clears the fence on the fly
    res = resolve_contact_outcome(110.0, 30.0, 0.0)
    assert res["call"] == "HOME_RUN"
    trace = res["batted_ball"]
    assert trace["fielded"] is False
    assert trace["fielding_type"] == "HOME_RUN"


def test_infield_grounder_out_vs_outfield_base_hit():
    # Routine grounder straight to SS (-18 deg)
    ground_out = resolve_contact_outcome(92.0, 2.0, -18.0)
    assert ground_out["call"] == "IN_PLAY_OUT"
    assert ground_out["batted_ball"]["fielded"] is True
    assert ground_out["batted_ball"]["fielder_id"] == "SS"
    assert ground_out["batted_ball"]["fielding_type"] in ("GROUND_SCOOP", "BACKHAND_PICK")

    # Rocket grounder through the gap (105 mph, -33.6 deg) reaches outfield grass
    gap_hit = resolve_contact_outcome(105.0, 0.0, -33.6)
    assert gap_hit["call"] in ("SINGLE", "DOUBLE")


def test_outfield_ball_touching_turf_is_clean_hit_with_retrieval_metadata():
    # 104 mph line drive into left-center gap (16 deg launch, -15 spray)
    # Drops onto outfield grass at ~304 ft, then fielded by LF on the bounce
    res = resolve_contact_outcome(104.0, 16.0, -15.0)
    assert res is not None
    assert res["call"] in ("DOUBLE", "SINGLE")
    batted = res["batted_ball"]
    assert batted["fielded"] is True
    assert batted["fielding_type"] == "GROUND_SCOOP"
    assert batted["is_clean_hit"] is True

    # And check that an airborne catch has is_clean_hit is False
    caught = resolve_contact_outcome(95.0, 25.0, 0.0)
    assert caught["call"] == "IN_PLAY_OUT"
    assert caught["batted_ball"]["is_clean_hit"] is False


def test_all_batted_ball_base_hits_are_called_singles_pending_baserunners():
    # Gap hit (95 mph, 20 deg launch, 40 deg spray) lands in RF gap -> SINGLE
    gap = resolve_contact_outcome(95.0, 20.0, 40.0)
    assert gap['call'] == 'SINGLE'
    assert gap['batted_ball']['is_clean_hit'] is True

    # Deep gap hit (104 mph, 16 deg, -15 spray) lands in left-center at 304 ft -> SINGLE
    deep_gap = resolve_contact_outcome(104.0, 16.0, -15.0)
    assert deep_gap['call'] == 'SINGLE'
    assert deep_gap['batted_ball']['is_clean_hit'] is True

    # Deep line drive into left-center gap (105 mph, 18 deg, -20 spray, 333 ft) -> SINGLE
    wall = resolve_contact_outcome(105.0, 18.0, -20.0)
    assert wall['call'] == 'SINGLE'
    assert wall['batted_ball']['is_clean_hit'] is True

    # Clean grounder through the 5.5 hole (-33.6 deg, 105 mph) -> SINGLE
    grounder = resolve_contact_outcome(105.0, 0.0, -33.6)
    assert grounder['call'] == 'SINGLE'
    assert grounder['batted_ball']['is_clean_hit'] is True



