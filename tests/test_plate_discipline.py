"""
Plate-discipline calibration tests for the swing/take decision model.

The headline metrics are measured on a deterministic seeded game log so they
reflect the actual pitch-location and count mix produced by the game engine.
"""

import json
import random
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database.db import get_player
from backend.engine.batting_engine.batter_strategy import (
    MODEL_CONFIG,
    BatterStrategy,
)
from backend.engine.batting_engine.batters import BatterInstanceManager
from backend.engine.game_engine import GameEngine

COUNTS = [
    (0, 0), (1, 0), (2, 0), (3, 0),
    (0, 1), (1, 1), (2, 1), (3, 1),
    (0, 2), (1, 2), (2, 2), (3, 2),
]
PITCH_PROFILES = {
    'Fastball': {
        'pitch_category': 'Fastball',
        'velocity_mph': 93.0,
        'horizontal_break_in': 6.0,
        'induced_vertical_break_in': 10.0,
    },
    'Breaking': {
        'pitch_category': 'Breaking',
        'velocity_mph': 84.0,
        'horizontal_break_in': 10.0,
        'induced_vertical_break_in': 20.0,
    },
    'OffSpeed': {
        'pitch_category': 'OffSpeed',
        'velocity_mph': 86.0,
        'horizontal_break_in': 8.0,
        'induced_vertical_break_in': 12.0,
    },
}
ZONE_INFO = {
    'heart': ('HEART', True, 'heart'),
    'shadow_strike': ('SHADOW', True, 'lower-away'),
    'shadow_ball': ('SHADOW', False, 'chase-away'),
    'chase': ('CHASE', False, 'chase-away'),
    'waste': ('WASTE', False, 'chase-high'),
}
NEUTRAL_ZONES = {
    zone: 0.40
    for zone in (
        'upper-in', 'upper-middle', 'upper-away',
        'middle-in', 'heart', 'middle-away',
        'lower-in', 'lower-middle', 'lower-away',
        'chase-high', 'chase-low', 'chase-in', 'chase-away',
    )
}


def _ratings(vision=60.0, zones=None):
    batter = {
        'id': 1,
        'name': 'Calibration Batter',
        'handedness': 'R',
        'ratings': {
            'power': 60.0,
            'contact': 60.0,
            'vision': vision,
            'speed': 60.0,
        },
        'zones': zones or NEUTRAL_ZONES,
    }
    return BatterInstanceManager.get_adjusted_ratings(batter)


def _delivery(
    category,
    is_strike,
    pitch_type='Fastball',
    effectiveness=50.0,
    effective_break=80.0,
):
    delivery = dict(PITCH_PROFILES[pitch_type])
    delivery.update({
        'realized_zone_cat': category,
        'is_strike': is_strike,
        'pitch_effectiveness': effectiveness,
        'adjusted_ratings': {'effective_break': effective_break},
    })
    return delivery


def _probability(model, count, zone_class, pitch_type='Fastball', **kwargs):
    category, is_strike, zone_name = ZONE_INFO[zone_class]
    delivery = _delivery(
        category,
        is_strike,
        pitch_type,
        effectiveness=kwargs.pop('effectiveness', 50.0),
        effective_break=kwargs.pop('effective_break', 80.0),
    )
    return model.evaluate_swing(
        delivery,
        actual_zone_name=zone_name,
        balls=count[0],
        strikes=count[1],
        **kwargs,
    ).probability


def _seeded_game(seed):
    pitcher = get_player(1)
    batter = get_player(4)
    roster = {
        'name': 'Calibration',
        'position_players': [batter],
        'pitchers': {'starters': [pitcher], 'bullpen': []},
    }
    return GameEngine(roster, roster, 'Home', 'Away', seed=seed)


def _collect_pitch_log(target=4000, max_games=40):
    rows = []
    seed = 2026
    games = 0
    while len(rows) < target and games < max_games:
        game = _seeded_game(seed)
        for _ in range(3000):
            if game.game_over:
                break
            thrown = game.throw_pitch()
            if thrown.get('status') != 'success':
                break
            pending = game.orchestrator.pending
            if pending is None:
                break
            resolved = game.resolve_pitch()
            if resolved.get('status') != 'success':
                break
            details = resolved['pitch_details']
            rows.append({
                'balls': pending.balls,
                'strikes': pending.strikes,
                'is_strike': pending.is_strike,
                'swing': details['batter_decision'] == 'SWING',
            })
        seed += 1
        games += 1
    return rows


def _rate(rows, predicate):
    selected = [row for row in rows if predicate(row)]
    assert selected
    return sum(1 for row in selected if row['swing']) / len(selected)


def test_league_plate_discipline_bands():
    rows = _collect_pitch_log()
    assert len(rows) >= 4000

    three_ball = [row for row in rows if row['balls'] == 3 and row['strikes'] == 0]
    assert len(three_ball) >= 20

    overall = _rate(rows, lambda row: True)
    in_zone = _rate(rows, lambda row: row['is_strike'])
    chase = _rate(rows, lambda row: not row['is_strike'])
    first_pitch = _rate(
        rows, lambda row: row['balls'] == 0 and row['strikes'] == 0
    )
    three_ball_rate = _rate(
        rows, lambda row: row['balls'] == 3 and row['strikes'] == 0
    )
    two_strike_chase = _rate(
        rows, lambda row: row['strikes'] == 2 and not row['is_strike']
    )

    assert 0.46 <= overall <= 0.49, overall
    assert 0.65 <= in_zone <= 0.69, in_zone
    assert 0.27 <= chase <= 0.32, chase
    assert 0.28 <= first_pitch <= 0.32, first_pitch
    assert 0.08 <= three_ball_rate <= 0.17, three_ball_rate
    assert 0.43 <= two_strike_chase <= 0.49, two_strike_chase


def test_approach_modes_are_directional_and_bounded():
    ratings = _ratings()
    auto = BatterStrategy(ratings, rng=random.Random(1))
    aggressive = BatterStrategy(ratings, rng=random.Random(1))
    patient = BatterStrategy(ratings, rng=random.Random(1))
    contact = BatterStrategy(ratings, rng=random.Random(1))

    strike_auto = _probability(auto, (1, 1), 'shadow_strike')
    strike_aggressive = _probability(
        aggressive, (1, 1), 'shadow_strike', approach_mode='AGGRESSIVE'
    )
    strike_patient = _probability(
        patient, (1, 1), 'shadow_strike', approach_mode='PATIENT'
    )
    strike_contact = _probability(
        contact, (1, 1), 'shadow_strike', approach_mode='CONTACT'
    )

    assert strike_aggressive > strike_auto
    assert strike_patient < strike_auto
    assert strike_contact > strike_auto
    assert strike_aggressive - strike_auto <= 0.12
    assert strike_patient - strike_auto >= -0.06
    assert strike_contact - strike_auto <= 0.10

    chase_auto = _probability(auto, (1, 1), 'chase')
    chase_aggressive = _probability(
        aggressive, (1, 1), 'chase', approach_mode='AGGRESSIVE'
    )
    chase_patient = _probability(
        patient, (1, 1), 'chase', approach_mode='PATIENT'
    )
    chase_contact = _probability(
        contact, (1, 1), 'chase', approach_mode='CONTACT'
    )

    assert chase_aggressive > chase_auto
    assert chase_patient < chase_auto
    assert chase_contact > chase_auto
    assert chase_auto - chase_patient >= 0.04
    assert chase_aggressive - chase_auto <= 0.10


def test_hot_cold_zone_effects_are_bounded():
    neutral = BatterStrategy(_ratings())
    hot_zones = dict(NEUTRAL_ZONES)
    cold_zones = dict(NEUTRAL_ZONES)
    hot_zones['heart'] = 0.62
    cold_zones['heart'] = 0.24
    hot = BatterStrategy(_ratings(zones=hot_zones))
    cold = BatterStrategy(_ratings(zones=cold_zones))

    neutral_strike = _probability(neutral, (1, 1), 'heart')
    hot_strike = _probability(hot, (1, 1), 'heart')
    cold_strike = _probability(cold, (1, 1), 'heart')

    assert hot_strike > neutral_strike > cold_strike
    assert 0.02 <= hot_strike - neutral_strike <= 0.10
    assert 0.02 <= neutral_strike - cold_strike <= 0.10

    hot_zones['chase-away'] = 0.45
    cold_zones['chase-away'] = 0.27
    hot_chase = BatterStrategy(_ratings(zones=hot_zones))
    cold_chase = BatterStrategy(_ratings(zones=cold_zones))
    hot_ball = _probability(hot_chase, (1, 1), 'chase')
    cold_ball = _probability(cold_chase, (1, 1), 'chase')
    assert hot_ball > cold_ball
    assert hot_ball - cold_ball <= 0.05


def test_pitch_type_changes_swing_behavior():
    model = BatterStrategy(_ratings())

    fastball_strike = _probability(model, (1, 1), 'shadow_strike', 'Fastball')
    breaking_strike = _probability(model, (1, 1), 'shadow_strike', 'Breaking')
    fastball_chase = _probability(model, (1, 1), 'chase', 'Fastball')
    breaking_chase = _probability(model, (1, 1), 'chase', 'Breaking')
    two_strike_fastball = _probability(model, (1, 2), 'chase', 'Fastball')
    two_strike_breaking = _probability(model, (1, 2), 'chase', 'Breaking')

    assert breaking_strike < fastball_strike
    assert breaking_chase > fastball_chase
    assert two_strike_breaking > two_strike_fastball
    assert two_strike_breaking - two_strike_fastball >= 0.02


def test_pitcher_stuff_increases_breaking_chase_but_not_in_zone_swing():
    model = BatterStrategy(_ratings())
    average_chase = _probability(
        model, (1, 2), 'chase', 'Breaking', effective_break=80.0
    )
    elite_chase = _probability(
        model, (1, 2), 'chase', 'Breaking', effective_break=98.0
    )
    average_strike = _probability(
        model, (1, 2), 'shadow_strike', 'Breaking', effective_break=80.0
    )
    elite_strike = _probability(
        model, (1, 2), 'shadow_strike', 'Breaking', effective_break=98.0
    )

    assert elite_chase > average_chase
    assert 0.01 <= elite_chase - average_chase <= 0.06
    assert elite_strike == pytest.approx(average_strike)


def test_sequence_repetition_reduces_chase_and_raises_strike_readiness():
    model = BatterStrategy(_ratings())
    breaking = {
        'pitch_category': 'Breaking',
        'result': 'SWINGING_STRIKE',
    }
    fastball = {
        'pitch_category': 'Fastball',
        'result': 'BALL',
    }

    no_history_chase = _probability(model, (1, 1), 'chase', 'Breaking')
    one_breaking_chase = _probability(
        model, (1, 1), 'chase', 'Breaking', pitch_sequence=[breaking]
    )
    two_breaking_chase = _probability(
        model, (1, 1), 'chase', 'Breaking', pitch_sequence=[breaking, breaking]
    )
    assert one_breaking_chase < no_history_chase
    assert two_breaking_chase < one_breaking_chase
    assert no_history_chase - two_breaking_chase <= 0.08

    no_history_strike = _probability(model, (1, 1), 'shadow_strike', 'Breaking')
    repeated_strike = _probability(
        model,
        (1, 1),
        'shadow_strike',
        'Breaking',
        pitch_sequence=[breaking, breaking],
    )
    assert repeated_strike > no_history_strike
    assert repeated_strike - no_history_strike <= 0.06

    mixed_chase = _probability(
        model, (1, 1), 'chase', 'Breaking', pitch_sequence=[fastball]
    )
    assert mixed_chase <= no_history_chase
    assert no_history_chase - mixed_chase <= 0.02


def test_situation_effects_are_small_and_directional():
    model = BatterStrategy(_ratings())
    neutral = _probability(model, (1, 1), 'shadow_strike')
    runner_on_third = _probability(
        model, (1, 1), 'shadow_strike', runners=(False, False, True), outs=0
    )
    blowout = _probability(
        model, (1, 1), 'shadow_strike', score_diff=6, inning=7
    )
    close_late = _probability(
        model, (1, 1), 'shadow_strike', score_diff=1, inning=8
    )

    assert runner_on_third > neutral
    assert 0.005 <= runner_on_third - neutral <= 0.04
    assert blowout < neutral
    assert close_late > neutral
    assert abs(blowout - neutral) <= 0.03
    assert abs(close_late - neutral) <= 0.03


def test_high_vision_chases_less_than_low_vision_but_not_extremely():
    high = BatterStrategy(_ratings(vision=95.0))
    low = BatterStrategy(_ratings(vision=40.0))
    high_chase = _probability(high, (1, 1), 'chase', 'Breaking')
    low_chase = _probability(low, (1, 1), 'chase', 'Breaking')
    assert 0.08 <= low_chase - high_chase <= 0.22


def test_evaluation_breakdown_sums_to_logit_and_is_bounded():
    model = BatterStrategy(_ratings(), rng=random.Random(3))
    evaluation = model.evaluate_swing(
        _delivery('CHASE', False, 'Breaking'),
        actual_zone_name='chase-away',
        balls=1,
        strikes=2,
        pitch_sequence=[{'pitch_category': 'Breaking', 'result': 'FOUL'}],
        outs=1,
        runners=(True, False, False),
        score_diff=1,
        inning=8,
        approach_mode='CONTACT',
    )

    assert evaluation.probability == pytest.approx(
        1.0 / (1.0 + pow(2.718281828459045, -evaluation.logit)),
        abs=1e-6,
    )
    assert 0.01 <= evaluation.probability <= 0.99
    assert set(evaluation.factors) == {
        'count', 'two_strike', 'discipline', 'hot_cold', 'pitch_type',
        'velocity', 'movement', 'pitcher_stuff', 'sequence', 'situation',
        'approach',
    }
    assert evaluation.model_version == MODEL_CONFIG['model_version']

    breakdown = evaluation.to_dict()
    assert set(breakdown) == {
        'model_version', 'will_swing', 'probability', 'base_logit', 'logit',
        'zone_class', 'count_key', 'factors',
    }


def test_at_bat_sequence_is_tracked_and_cleared_after_the_pa():
    game = _seeded_game(99)
    game.throw_pitch()
    game.resolve_pitch(batter_decision='TAKE')
    assert len(game.current_at_bat_pitches) == 1

    game.sim_at_bat()
    assert game.current_at_bat_pitches == []


def test_debug_swing_telemetry_is_optional(monkeypatch):
    import backend.engine.game_engine.engine as engine_module

    monkeypatch.setattr(engine_module, 'SWING_DECISION_TELEMETRY', False)
    game = _seeded_game(99)
    details = game.pitch()['pitch_details']
    assert 'swing_decision' not in details

    monkeypatch.setattr(engine_module, 'SWING_DECISION_TELEMETRY', True)
    game = _seeded_game(99)
    details = game.pitch()['pitch_details']
    decision = details['swing_decision']
    assert decision['model_version'] == MODEL_CONFIG['model_version']
    assert 0.0 < decision['probability'] < 1.0
    assert 'factors' in decision and 'zone_class' in decision


def test_seeded_decisions_are_reproducible():
    first = BatterStrategy(_ratings(), rng=random.Random(17))
    second = BatterStrategy(_ratings(), rng=random.Random(17))
    delivery = _delivery('SHADOW', True, 'Fastball')
    for count in COUNTS:
        assert first.decide_swing(
            delivery,
            actual_zone_name='lower-away',
            balls=count[0],
            strikes=count[1],
        ) == second.decide_swing(
            delivery,
            actual_zone_name='lower-away',
            balls=count[0],
            strikes=count[1],
        )


def test_parity_fixture_matches_backend_model():
    fixture_path = (
        ROOT_DIR / 'tests' / 'fixtures' / 'swing_model_parity_cases.json'
    )
    cases = json.loads(fixture_path.read_text())
    assert len(cases) >= 20

    for entry in cases:
        ratings_payload = entry['ratings']
        batter = {
            'id': 1,
            'name': 'Parity Batter',
            'handedness': 'R',
            'ratings': {
                'power': 60.0,
                'contact': 60.0,
                'vision': ratings_payload['vision'],
                'speed': 60.0,
            },
            'zones': ratings_payload['hotZones'],
        }
        ratings = BatterInstanceManager.get_adjusted_ratings(batter)
        delivery = entry['delivery']
        situation = entry['situation']
        sequence = [
            {
                'pitch_category': pitch['pitchCategory'],
                'result': pitch.get('result'),
            }
            for pitch in situation.get('pitchSequence', [])
        ]
        evaluation = BatterStrategy(ratings).evaluate_swing(
            {
                'pitch_category': delivery['pitchCategory'],
                'velocity_mph': delivery['velocityMph'],
                'horizontal_break_in': delivery['horizontalBreakIn'],
                'induced_vertical_break_in': delivery['inducedVerticalBreakIn'],
                'realized_zone_cat': delivery['zoneCategory'],
                'is_strike': delivery['isStrike'],
                'adjusted_ratings': {
                    'effective_break': delivery['pitcherEffectiveBreak'],
                },
            },
            actual_zone_name=delivery['zoneName'],
            balls=situation['balls'],
            strikes=situation['strikes'],
            approach_mode=situation['approach'],
            pitch_sequence=sequence,
            outs=situation['outs'],
            runners=tuple(situation['runners']),
            score_diff=situation['scoreDiff'],
            inning=situation['inning'],
            pitcher_ratings={
                'effective_break': delivery['pitcherEffectiveBreak'],
            },
        )
        assert evaluation.probability == pytest.approx(
            entry['expectedProbability'], abs=1e-8
        )


def test_swing_config_is_synced_to_the_frontend():
    backend_path = (
        ROOT_DIR / 'backend' / 'engine' / 'batting_engine' /
        'swing_model_config.json'
    )
    frontend_path = (
        ROOT_DIR / 'frontend' / 'app' / 'src' / 'services' /
        'swingModelConfig.json'
    )
    assert frontend_path.exists(), 'frontend swing model config is missing'
    assert json.loads(backend_path.read_text()) == json.loads(
        frontend_path.read_text()
    )


def test_config_contains_every_zone_class_and_approach_mode():
    for zone_class in ('heart', 'shadow_strike', 'shadow_ball', 'chase', 'waste'):
        assert zone_class in MODEL_CONFIG['zone_logit']
        assert zone_class in MODEL_CONFIG['three_ball_no_strike']
    for mode in ('AUTO', 'AGGRESSIVE', 'PATIENT', 'CONTACT'):
        assert mode in MODEL_CONFIG['approach']
