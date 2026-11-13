#!/usr/bin/env python3
"""
Pitch selection contract tests.

Covers AI vs. user selection, the tactical ``pitch_intent`` semantics, target
resolution precedence, practice forcing, and the API contract.
"""

from pathlib import Path
import random
import sys
from unittest.mock import patch

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.api.app import create_app
from backend.database.db import get_player
from backend.engine.game_engine import GameEngine
from backend.engine.game_engine.gameday_math import (
    CHASE_BORDER_FT,
    ZONE_X_MAX,
    ZONE_X_MIN,
    ZONE_Z_BOT,
    ZONE_Z_TOP,
    classify_gameday_zone,
    is_rulebook_strike,
)
from backend.engine.pitching_engine import PitchingEngine
from backend.engine.pitching_engine.pitch_selection import (
    PitchSelectionError,
    PitchSelectionMode,
    PitchStrategy,
    select_pitch,
)
from backend.engine.pitching_engine.pitch_selection.intent import pitch_specific_zone


def _matchup():
    """Fixture: Nolan McLean (pitcher) and Aaron Judge (batter)."""
    p1 = get_player(1)
    p2 = get_player(2)
    pitcher = p1 if p1 and p1.is_pitcher else p2
    batter = p2 if p1 and p1.is_pitcher else p1
    assert pitcher is not None
    assert batter is not None
    return pitcher, batter


def _engine(seed: int = 7) -> PitchingEngine:
    pitcher, batter = _matchup()
    return PitchingEngine(pitcher, batter, rng=random.Random(seed))


def _select(engine: PitchingEngine, **kwargs):
    kwargs.setdefault('balls', 0)
    kwargs.setdefault('strikes', 0)
    kwargs.setdefault('rng', engine.rng)
    return select_pitch(engine.strategy, engine.arsenal, **kwargs)


def test_ai_selection_returns_an_arsenal_pitch():
    engine = _engine()
    selection = _select(engine, selection_mode='ai')

    arsenal_names = {pitch.name for pitch in engine.arsenal.pitches}
    assert selection.mode is PitchSelectionMode.AI
    assert selection.source == 'AI'
    assert selection.pitch_name in arsenal_names
    assert selection.pitch is not None
    assert selection.pitch.name == selection.pitch_name


def test_user_selection_returns_the_requested_pitch():
    engine = _engine()
    selection = _select(
        engine,
        selection_mode='user',
        pitch_name='Spin Monster Sweeper',
    )

    assert selection.mode is PitchSelectionMode.USER
    assert selection.source == 'USER'
    assert selection.pitch_name == 'Spin Monster Sweeper'
    assert selection.pitch is not None
    assert selection.velocity_mph == float(selection.pitch.velocity_mph)
    assert selection.spin_rpm == int(selection.pitch.spin_rpm)


def test_user_selection_is_case_insensitive_and_rejects_unknown_names():
    engine = _engine()

    lowered = _select(
        engine,
        selection_mode='user',
        pitch_name='spin monster sweeper',
    )
    assert lowered.pitch_name == 'Spin Monster Sweeper'

    with pytest.raises(PitchSelectionError):
        _select(engine, selection_mode='user', pitch_name='Not A Real Pitch')


def test_four_seam_spellings_resolve_to_the_arsenal_pitch():
    engine = _engine()
    selection = _select(
        engine,
        selection_mode='user',
        pitch_name='4-Seam Fastball',
    )
    assert selection.pitch_name == 'Four-Seam Fastball'
    assert selection.pitch is not None


def test_state_payload_exposes_the_real_pitcher_arsenal():
    pitcher, batter = _matchup()
    game = GameEngine(
        {'name': 'New York Mets', 'position_players': [batter], 'pitchers': {'starters': [pitcher], 'bullpen': []}},
        {'name': 'New York Yankees', 'position_players': [batter], 'pitchers': {'starters': [pitcher], 'bullpen': []}},
        'Mets',
        'Yankees',
    )

    payload = game.get_game_state_payload()
    expected_names = [item['name'] for item in pitcher.pitch_arsenal]
    assert [item['name'] for item in payload['current_pitcher']['arsenal']] == expected_names
    assert payload['current_pitcher']['arsenal'][0]['velocity_mph'] == pytest.approx(
        pitcher.pitch_arsenal[0]['velocity_mph']
    )


def test_user_selection_requires_a_pitch_name():
    engine = _engine()
    with pytest.raises(PitchSelectionError):
        _select(engine, selection_mode='user')

    with pytest.raises(PitchSelectionError):
        _select(engine, selection_mode='user', pitch_name='')


def test_pitch_name_is_inferred_for_legacy_callers():
    engine = _engine()
    selection = _select(engine, pitch_name='Power Sinker')
    assert selection.mode is PitchSelectionMode.USER
    assert selection.pitch_name == 'Power Sinker'


def test_ai_mode_rejects_a_pitch_field():
    engine = _engine()
    with pytest.raises(PitchSelectionError):
        _select(engine, selection_mode='ai', pitch_name='Power Sinker')


def test_pitch_intent_never_changes_the_selected_pitch():
    engine = _engine()
    names = set()
    for intent in (None, 'STRIKE', 'CHASE', 'WASTE'):
        selection = _select(
            engine,
            selection_mode='user',
            pitch_name='Spike Curveball',
            pitch_intent=intent,
        )
        names.add(selection.pitch_name)
    assert names == {'Spike Curveball'}


def test_strike_intent_suppresses_the_ball_intent_mix():
    engine = _engine()
    with patch(
        'backend.engine.pitching_engine.pitch_selection.intent.mix_ball_intent'
    ) as mixer:
        selection = _select(engine, pitch_intent='STRIKE')

    mixer.assert_not_called()
    target = selection.target_intent
    assert target.nominal_zone == 'lower-away'
    assert is_rulebook_strike(target.target_x, target.target_z)


def test_strike_intent_falls_back_to_heart_for_chase_recommendations():
    engine = _engine()
    # Two strikes recommends chase-away; STRIKE must fall back into the zone.
    selection = _select(engine, balls=0, strikes=2, pitch_intent='STRIKE')
    target = selection.target_intent
    assert target.nominal_zone == 'heart'
    assert is_rulebook_strike(target.target_x, target.target_z)


def test_chase_intent_forces_a_chase_target():
    for seed in range(10):
        engine = _engine(seed=seed)
        selection = _select(engine, pitch_intent='CHASE')
        target = selection.target_intent
        assert target.nominal_zone in ('chase-low', 'chase-away')
        assert target.intended_zone_cat == 'CHASE'
        assert not is_rulebook_strike(target.target_x, target.target_z)


def test_waste_intent_forces_a_target_beyond_the_chase_band():
    for seed in range(10):
        engine = _engine(seed=seed)
        selection = _select(engine, pitch_intent='WASTE')
        target = selection.target_intent
        assert target.intended_zone_cat == 'WASTE'
        assert classify_gameday_zone(target.target_x, target.target_z) == 'WASTE'
        outside_chase = (
            target.target_x < ZONE_X_MIN - CHASE_BORDER_FT
            or target.target_x > ZONE_X_MAX + CHASE_BORDER_FT
            or target.target_z < ZONE_Z_BOT - CHASE_BORDER_FT
            or target.target_z > ZONE_Z_TOP + CHASE_BORDER_FT
        )
        assert outside_chase


def test_omitted_intent_preserves_the_ball_intent_mix():
    engine = _engine()
    with patch(
        'backend.engine.pitching_engine.pitch_selection.intent.mix_ball_intent',
        return_value='chase-low',
    ) as mixer:
        selection = _select(engine)

    mixer.assert_called_once()
    assert selection.target_intent.nominal_zone == 'chase-low'


def test_invalid_pitch_intent_is_rejected():
    engine = _engine()
    with pytest.raises(PitchSelectionError):
        _select(engine, pitch_intent='FASTBALL')


def test_pitch_specific_target_bias_maps_four_seam_and_sinker():
    assert pitch_specific_zone('lower-away', '4-Seam Fastball', 'R', 'R') == 'upper-away'
    assert pitch_specific_zone('upper-middle', '4-Seam Fastball', 'R', 'R') == 'upper-middle'
    assert pitch_specific_zone('heart', 'Power Sinker', 'R', 'R') == 'lower-middle'
    assert pitch_specific_zone('middle-in', 'Power Sinker', 'R', 'R') == 'lower-in'
    assert pitch_specific_zone('middle-in', 'Power Sinker', 'L', 'R') == 'lower-away'
    assert pitch_specific_zone('chase-low', 'Power Sinker', 'R', 'R') == 'chase-low'


def test_user_pitch_specific_target_bias_applies_without_an_explicit_intent():
    engine = _engine()
    with patch(
        'backend.engine.pitching_engine.pitch_selection.intent.mix_ball_intent',
        side_effect=lambda recommended_zone, *args, **kwargs: recommended_zone,
    ):
        four = _select(
            engine,
            selection_mode='user',
            pitch_name='4-Seam Fastball',
        )
        sinker = _select(
            engine,
            selection_mode='user',
            pitch_name='Power Sinker',
        )

    assert four.target_intent.nominal_zone == 'upper-away'
    assert sinker.target_intent.nominal_zone == 'lower-away'


def test_explicit_intent_or_target_is_not_overridden_by_pitch_shape():
    engine = _engine()
    explicit_intent = _select(
        engine,
        selection_mode='user',
        pitch_name='4-Seam Fastball',
        pitch_intent='STRIKE',
    )
    explicit_target = _select(
        engine,
        selection_mode='user',
        pitch_name='4-Seam Fastball',
        target_zone='heart',
    )

    assert explicit_intent.target_intent.nominal_zone == 'lower-away'
    assert explicit_target.target_intent.nominal_zone == 'heart'


def test_execute_pitch_uses_the_user_pitch_in_delivery_telemetry():
    engine = _engine()
    pitch = engine.arsenal.get('Power Sinker')
    assert pitch is not None

    delivery = engine.execute_pitch(
        balls=0,
        strikes=0,
        selection_mode='user',
        pitch_name='Power Sinker',
        target_zone='heart',
    )

    assert delivery['selected_pitch'] == 'Power Sinker'
    assert delivery['velocity_mph'] == round(pitch.velocity_mph, 1)
    assert delivery['horizontal_break_in'] == pitch.horizontal_break_in
    assert delivery['induced_vertical_break_in'] == pitch.induced_vertical_break_in


def test_practice_delivery_builder_forces_the_pitch_and_exact_target():
    from backend.engine.modes.practice_mode import PracticeDeliveryBuilder
    engine = _engine()
    delivery = PracticeDeliveryBuilder.build(
        pitcher=engine.pitcher,
        arsenal=engine.arsenal,
        pitch_name='Spin Monster Sweeper',
        custom_target={'x': 0.0, 'z': 2.5},
    )

    assert delivery['selected_pitch'] == 'Spin Monster Sweeper'
    assert delivery['target_x'] == 0.0
    assert delivery['target_z'] == 2.5
    assert delivery['realized_x'] == 0.0
    assert delivery['realized_z'] == 2.5
    assert delivery['sigma'] == 0.0
    assert delivery['strat_result']['strategy_name'] == 'PRACTICE_DRILL'
    assert delivery['strat_result']['dynamic_modifier'] == 1.0


def test_recommendation_payload_still_matches_the_documented_shape():
    pitcher, batter = _matchup()
    game = GameEngine(
        {'name': 'New York Mets', 'position_players': [batter], 'pitchers': {'starters': [pitcher], 'bullpen': []}},
        {'name': 'New York Yankees', 'position_players': [batter], 'pitchers': {'starters': [pitcher], 'bullpen': []}},
        'Mets',
        'Yankees',
    )

    payload = game.calculate_strategy_and_intent()
    assert set(payload) == {
        'strategy_name',
        'situation_tag',
        'count_context',
        'rationale',
        'recommended_pitch',
        'recommended_zone',
        'pitch_weights',
        'zone_weights',
        'command_quality',
    }
    assert payload['pitch_weights']
    assert payload['zone_weights']
    assert payload['recommended_pitch']


@pytest.fixture()
def client():
    client = create_app().test_client()
    assert client.post('/api/start_game', json={'seed': 2027}).status_code == 200
    return client


def _throw(client, payload):
    response = client.post('/api/pitch/throw', json=payload)
    if response.status_code == 200:
        assert client.post(
            '/api/pitch/resolve', json={'batter_decision': 'TAKE'}
        ).status_code == 200
    return response


def test_api_accepts_ai_and_user_requests(client):
    ai = _throw(client, {'selection_mode': 'ai'})
    assert ai.status_code == 200
    assert ai.get_json()['pitch_details']['pitch_name']

    user = _throw(
        client,
        {
            'selection_mode': 'user',
            'pitch_name': 'Spin Monster Sweeper',
            'target_zone': 'heart',
        },
    )
    assert user.status_code == 200
    assert user.get_json()['pitch_details']['pitch_name'] == 'Spin Monster Sweeper'

    legacy = _throw(client, {'pitch_type': 'Power Sinker', 'target_zone': 'heart'})
    assert legacy.status_code == 200
    assert legacy.get_json()['pitch_details']['pitch_name'] == 'Power Sinker'

    legacy_seam = _throw(
        client, {'pitch_name': '4-Seam Fastball', 'target_zone': 'heart'}
    )
    assert legacy_seam.status_code == 200
    assert legacy_seam.get_json()['pitch_details']['pitch_name'] == 'Four-Seam Fastball'


def test_api_rejects_ambiguous_or_invalid_selection_contracts(client):
    missing_name = _throw(client, {'selection_mode': 'user'})
    assert missing_name.status_code == 400

    unknown_name = _throw(
        client, {'selection_mode': 'user', 'pitch_name': 'Not A Real Pitch'}
    )
    assert unknown_name.status_code == 400

    ai_with_pitch = _throw(
        client, {'selection_mode': 'ai', 'pitch_name': 'Power Sinker'}
    )
    assert ai_with_pitch.status_code == 400

    invalid_intent = _throw(client, {'pitch_intent': 'FASTBALL'})
    assert invalid_intent.status_code == 400


def test_practice_api_forces_the_requested_pitch_and_exact_target(client):
    assert client.post('/api/practice/start', json={}).status_code == 200

    thrown = client.post(
        '/api/practice/pitch/throw',
        json={
            'pitch_name': 'Spin Monster Sweeper',
            'target_x': 0.1,
            'target_z': 2.4,
        },
    )
    assert thrown.status_code == 200
    details = thrown.get_json()['pitch_details']
    assert details['pitch_name'] == 'Spin Monster Sweeper'
    packet = details['gameday_packet']
    assert packet['intent']['targetX'] == 0.1
    assert packet['intent']['targetZ'] == 2.4
    assert packet['execution']['realizedX'] == 0.1
    assert packet['execution']['realizedZ'] == 2.4
