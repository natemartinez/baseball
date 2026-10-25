#!/usr/bin/env python3
"""
Batting Engine Test Suite.

Covers batter rating/zone normalization, swing-decision behavior, contact
monotonicity, deterministic execution, GameEngine two-phase integration,
telemetry correctness, API ordering, and seeded outcome calibration.
"""

import random
from collections import Counter
from pathlib import Path
import sys

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.api.app import create_app
from backend.database.db import get_player
from backend.engine.batting_engine import (
    BattingEngine,
    BatterActivity,
    BatterInstanceManager,
    BatterStrategy,
    ContactResolver,
    DEFAULT_BATTER_ZONES,
    InGameBatterRatings,
    normalize_hot_zones,
)
from backend.engine.game_engine import GameEngine
from backend.models.player import Player


def _ratings(
    power=60.0,
    contact=60.0,
    vision=60.0,
    speed=60.0,
    hand='R',
    zones=None,
    pitcher_hand='R',
) -> InGameBatterRatings:
    batter = {
        'id': 1,
        'name': 'Test Batter',
        'handedness': hand,
        'ratings': {
            'power': power,
            'contact': contact,
            'vision': vision,
            'speed': speed,
        },
        'zones': zones or {},
    }
    return BatterInstanceManager.get_adjusted_ratings(
        batter, pitcher_hand=pitcher_hand
    )


def _delivery(
    category='SHADOW',
    is_strike=True,
    pitch_category='Fastball',
    velocity=93.0,
    effectiveness=50.0,
    x=0.0,
    z=2.5,
):
    return {
        'selected_pitch': '4-Seam Fastball',
        'pitch_category': pitch_category,
        'velocity_mph': velocity,
        'spin_rpm': 2400,
        'horizontal_break_in': 6.0,
        'induced_vertical_break_in': 10.0,
        'realized_x': x,
        'realized_z': z,
        'realized_zone_cat': category,
        'is_strike': is_strike,
        'pitch_effectiveness': effectiveness,
    }


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


def test_normalize_hot_zones_uses_multiplier_and_neutral_defaults():
    neutral = normalize_hot_zones(None)
    assert neutral == DEFAULT_BATTER_ZONES
    assert neutral['heart'] == 0.470

    zones = normalize_hot_zones([{'name': 'heart', 'slg_multiplier': 1.5}])
    assert abs(zones['heart'] - 0.600) < 1e-9
    assert zones['chase-away'] == DEFAULT_BATTER_ZONES['chase-away']

    direct = normalize_hot_zones({'heart': 0.555})
    assert direct['heart'] == 0.555


def test_batter_ratings_come_from_the_actual_player():
    gleyber = get_player(4)
    ratings = BatterInstanceManager.get_adjusted_ratings(gleyber, pitcher_hand='R')
    assert ratings.power == 78
    assert ratings.contact == 82
    assert ratings.vision == 80
    assert ratings.speed == 70
    assert ratings.hot_zones['heart'] == DEFAULT_BATTER_ZONES['heart']

    judge = get_player(2)
    judge_ratings = BatterInstanceManager.get_adjusted_ratings(judge, pitcher_hand='R')
    assert judge_ratings.power == 99
    assert judge_ratings.hot_zones['heart'] != DEFAULT_BATTER_ZONES['heart']


def test_vision_and_count_change_swing_probability():
    chase = _delivery(category='CHASE', is_strike=False, x=1.2, z=2.5)

    low_vision = BatterStrategy(_ratings(vision=40), rng=random.Random(1))
    high_vision = BatterStrategy(_ratings(vision=95), rng=random.Random(1))

    low_prob = low_vision.decide_swing(
        chase, actual_zone_name='chase-away', balls=0, strikes=0
    )[1]
    high_prob = high_vision.decide_swing(
        chase, actual_zone_name='chase-away', balls=0, strikes=0
    )[1]
    assert high_prob < low_prob

    two_strike_prob = high_vision.decide_swing(
        chase, actual_zone_name='chase-away', balls=0, strikes=2
    )[1]
    assert two_strike_prob > high_prob

    green_light = high_vision.decide_swing(
        _delivery(category='HEART', is_strike=True),
        actual_zone_name='heart',
        balls=3,
        strikes=0,
    )[1]
    assert green_light <= 0.30


def test_whiff_and_exit_velocity_follow_ratings_and_pitch_quality():
    weak_batter = ContactResolver(_ratings(contact=40), rng=random.Random(3))
    strong_batter = ContactResolver(_ratings(contact=95), rng=random.Random(3))
    weak_whiff = weak_batter._whiff_probability(
        zone_category='SHADOW', is_strike=True, pitch_category='Fastball',
        velocity=95.0, movement=12.0, pitch_effectiveness=45.0,
        balls=0, strikes=0, approach_mode='AUTO',
    )
    strong_whiff = strong_batter._whiff_probability(
        zone_category='SHADOW', is_strike=True, pitch_category='Fastball',
        velocity=95.0, movement=12.0, pitch_effectiveness=45.0,
        balls=0, strikes=0, approach_mode='AUTO',
    )
    breaking_whiff = strong_batter._whiff_probability(
        zone_category='SHADOW', is_strike=True, pitch_category='Breaking',
        velocity=84.0, movement=25.0, pitch_effectiveness=75.0,
        balls=0, strikes=0, approach_mode='AUTO',
    )
    assert strong_whiff < weak_whiff
    assert breaking_whiff > strong_whiff

    def average_ev(power):
        resolver = ContactResolver(_ratings(power=power), rng=random.Random(11))
        values = []
        for _ in range(250):
            result = resolver._resolve_batted_ball(
                actual_zone_name='heart',
                pitch_name='4-Seam Fastball',
                pitch_category='Fastball',
                velocity=95.0,
                realized_x=0.0,
                realized_z=2.5,
            )
            values.append(result['exit_velocity_mph'])
        return sum(values) / len(values)

    assert average_ev(99) > average_ev(45) + 3.0


def test_batting_engine_is_deterministic_for_a_seed():
    batter = Player(
        name='Deterministic Batter',
        id=99,
        ratings={'power': 70, 'contact': 70, 'vision': 70, 'speed': 60},
        zones={'heart': 0.55},
    )
    delivery = _delivery(category='HEART', is_strike=True)
    kwargs = dict(
        balls=1,
        strikes=1,
        outs=0,
        runners=(False, False, False),
        situation='NEUTRAL',
        actual_zone_name='heart',
    )

    first = BattingEngine(batter, delivery, rng=random.Random(1234)).resolve(**kwargs)
    second = BattingEngine(batter, delivery, rng=random.Random(1234)).resolve(**kwargs)
    assert first.to_dict() == second.to_dict()
    assert first.call in {
        'BALL', 'CALLED_STRIKE', 'SWINGING_STRIKE', 'FOUL', 'IN_PLAY_OUT',
        'SINGLE', 'DOUBLE', 'TRIPLE', 'HOME_RUN',
    }


def test_game_engine_two_phase_applies_result_only_on_resolve():
    game = _game(seed=7)
    before = (game.balls, game.strikes, game.outs, dict(game.score))

    thrown = game.throw_pitch()
    assert thrown['status'] == 'success'
    assert thrown['phase'] == 'THROWN'
    assert (game.balls, game.strikes, game.outs, dict(game.score)) == before
    assert game.has_pending_pitch is True

    duplicate = game.throw_pitch()
    assert duplicate['status'] == 'error'

    resolved = game.resolve_pitch()
    assert resolved['status'] == 'success'
    assert resolved['phase'] == 'RESOLVED'
    assert game.has_pending_pitch is False
    assert resolved['pitch_details']['batter_decision'] in ('SWING', 'TAKE')


def test_seeded_game_engine_sequence_is_reproducible():
    first = _game(seed=2026)
    second = _game(seed=2026)

    for _ in range(12):
        thrown_a = first.throw_pitch()
        thrown_b = second.throw_pitch()
        assert thrown_a['pitch_details']['gameday_packet']['execution']['realizedX'] == (
            thrown_b['pitch_details']['gameday_packet']['execution']['realizedX']
        )
        assert thrown_a['pitch_details']['gameday_packet']['strategy']['selectedPitch'] == (
            thrown_b['pitch_details']['gameday_packet']['strategy']['selectedPitch']
        )

        resolved_a = first.resolve_pitch()
        resolved_b = second.resolve_pitch()
        assert resolved_a['pitch_details']['pitch_result'] == (
            resolved_b['pitch_details']['pitch_result']
        )
        assert resolved_a['pitch_details']['exit_velocity_mph'] == (
            resolved_b['pitch_details']['exit_velocity_mph']
        )


def test_game_state_reports_real_batter_telemetry_and_live_stats():
    gleyber_game = _game(seed=3, batter_id=4)
    payload = gleyber_game.get_game_state_payload()['current_batter']
    assert payload['power'] == 78
    assert payload['contact'] == 82
    assert payload['vision'] == 80
    assert payload['hot_zones']['heart'] == DEFAULT_BATTER_ZONES['heart']
    assert payload['stats'] == {'at_bats': 0, 'hits': 0, 'rbis': 0, 'home_runs': 0}

    judge_game = _game(seed=3, batter_id=2)
    judge_payload = judge_game.get_game_state_payload()['current_batter']
    assert judge_payload['power'] == 99
    assert judge_payload['hot_zones']['heart'] != DEFAULT_BATTER_ZONES['heart']
    assert 'DEAD_RED_PULL' in judge_payload['traits']

    gleyber_game.sim_at_bat()
    assert isinstance(
        gleyber_game.get_game_state_payload()['current_batter']['stats'], dict
    )


def test_game_engine_tracks_live_batting_line():
    game = _game(seed=5, batter_id=4)
    batter = get_player(4)
    activity = BatterActivity(
        decision='SWING',
        swing_probability=0.9,
        pitch_result='HOME_RUN',
        call='HOME_RUN',
        description='Home run',
        is_in_play=True,
        is_strike=False,
        zone_name='heart',
        zone_category='HEART',
        exit_velocity_mph=108.0,
        launch_angle_deg=27.0,
        spray_angle_deg=12.0,
        contact_quality='BARREL',
        batter_ratings={},
    )

    runs_before = game.score[game.away_name]
    game._apply_batter_activity(activity, batter)
    line = game._batter_game_stats[game._batter_stats_key(batter)]
    assert line == {'at_bats': 1, 'hits': 1, 'rbis': 1, 'home_runs': 1}
    assert game.score[game.away_name] == runs_before + 1


def test_seeded_outcome_distribution_is_baseball_like():
    pitcher = get_player(1)
    batter = Player(
        name='Average Batter',
        id=999,
        ratings={'power': 60, 'contact': 60, 'vision': 60, 'speed': 60},
        zones={},
    )

    def make_game(seed):
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

    results = []
    seed = 12345
    game = make_game(seed)
    while len(results) < 2000:
        if game.game_over:
            seed += 1
            game = make_game(seed)
        results.append(game.sim_at_bat()['pitch_details']['pitch_result'])

    counts = Counter(results)
    plate_appearances = len(results)
    strikeouts = counts['CALLED_STRIKE'] + counts['SWINGING_STRIKE']
    walks = counts['BALL']
    home_runs = counts['HOME_RUN']
    hits = counts['SINGLE'] + counts['DOUBLE'] + counts['TRIPLE']
    in_play_outs = counts['IN_PLAY_OUT']

    assert 0.18 <= strikeouts / plate_appearances <= 0.27
    assert 0.06 <= walks / plate_appearances <= 0.11
    assert 0.02 <= home_runs / plate_appearances <= 0.05
    assert 0.26 <= hits / max(1, hits + in_play_outs) <= 0.34


def test_two_phase_api_ordering_and_conflicts():
    client = create_app().test_client()
    response = client.post('/api/start_game', json={'seed': 9})
    assert response.status_code == 200

    before = client.get('/api/state').get_json()['game_state']
    thrown = client.post('/api/pitch/throw', json={})
    assert thrown.status_code == 200
    thrown_data = thrown.get_json()
    assert thrown_data['phase'] == 'THROWN'
    after_throw = client.get('/api/state').get_json()['game_state']
    assert (after_throw['balls'], after_throw['strikes'], after_throw['outs']) == (
        before['balls'], before['strikes'], before['outs']
    )

    duplicate = client.post('/api/pitch/throw', json={})
    assert duplicate.status_code == 409

    resolved = client.post('/api/pitch/resolve', json={})
    assert resolved.status_code == 200
    assert resolved.get_json()['phase'] == 'RESOLVED'

    missing = client.post('/api/pitch/resolve', json={})
    assert missing.status_code == 409
