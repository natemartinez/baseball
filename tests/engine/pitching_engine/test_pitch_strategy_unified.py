import pytest
from backend.database.db import get_player
from backend.engine.pitching_engine.pitch_selection.strategy import (
    PitchStrategy,
    calculate_strategy_and_intent,
)
from backend.engine.pitching_engine.pitcher_info import ActivePitcherState


def test_pitch_strategy_evaluate_matchup_returns_plan():
    pitcher = get_player(1)
    batter = get_player(2)
    strategy = PitchStrategy(pitcher, batter)

    plan = strategy.evaluate_matchup()
    assert plan is not None
    assert plan.pitcher_hand == 'R'
    assert plan.batter_side == 'R'
    assert strategy.matchup_plan is plan


def test_pitch_strategy_build_plan_unified_payload():
    pitcher = get_player(1)
    batter = get_player(2)
    strategy = PitchStrategy(pitcher, batter)

    res = strategy.build_plan(balls=0, strikes=2)
    expected_keys = {
        'strategy_name',
        'situation_tag',
        'count_context',
        'rationale',
        'recommended_pitch',
        'recommended_zone',
        'pitch_weights',
        'zone_weights',
        'command_quality',
        'repertoire_probabilities',
        'dynamic_modifier',
    }
    assert expected_keys.issubset(set(res.keys()))
    # Recommended pitch must be the #1 ranked pitch CPU would choose
    assert res['recommended_pitch'] == res['pitch_weights'][0]['pitch_name']
    assert res['recommended_zone']
    assert len(res['pitch_weights']) > 0
    assert len(res['zone_weights']) == 13


def test_calculate_strategy_and_intent_helper_in_strategy():
    pitcher = get_player(1)
    batter = get_player(2)
    payload = calculate_strategy_and_intent(
        outs=1,
        balls=3,
        strikes=2,
        bases={'first': 1, 'second': None, 'third': None},
        batter=batter,
        pitcher=pitcher,
    )
    assert payload['strategy_name']
    assert payload['recommended_pitch']
    assert payload['recommended_zone']
    assert len(payload['pitch_weights']) > 0
    assert len(payload['zone_weights']) == 13


def test_pitch_strategy_cross_at_bat_decay():
    pitcher = get_player(1)
    batter = get_player(2)
    state = ActivePitcherState.from_player(pitcher)
    # Throw 3 sweepers in earlier at-bats to this batter
    for _ in range(3):
        state.record_at_bat_pitch(batter, 'Spin Monster Sweeper')

    strategy = PitchStrategy(pitcher, batter, active_state=state)
    res = strategy.build_plan(balls=0, strikes=0)
    assert res['dynamic_modifier'] <= 1.0

