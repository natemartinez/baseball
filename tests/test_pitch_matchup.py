import pytest
from backend.database.db import get_player
from backend.engine.pitching_engine.pitcher_info.pitch_objects import PitchArsenal
from backend.engine.pitching_engine.pitch_selection.matchup import (
    BatterMatchupPlan,
    evaluate_platoon_and_arsenal,
)


def test_evaluate_platoon_same_handed():
    p1 = get_player(1)  # Nolan McLean (RHP)
    p2 = get_player(2)  # Aaron Judge (RHB)
    arsenal = PitchArsenal.extract_from_pitcher(p1)
    plan = evaluate_platoon_and_arsenal(p1, p2, arsenal)

    assert isinstance(plan, BatterMatchupPlan)
    assert plan.pitcher_hand == 'R'
    assert plan.batter_side == 'R'
    assert plan.platoon_advantage == 'PITCHER'
    assert 'Spin Monster Sweeper' in plan.pitch_base_weights
    # Breaking ball running away from same-hand batter receives platoon boost
    assert plan.pitch_base_weights['Spin Monster Sweeper'] > 0
    assert plan.primary_weapon is not None
    assert plan.recommended_attack_zone is not None


def test_evaluate_platoon_switch_hitter():
    p1 = get_player(1)  # RHP
    switch_batter = {
        'name': 'Switch Batter',
        'id': 99,
        'vitals': {'bats': 'S'},
        'hot_zones': {'heart': 0.6},
    }
    plan = evaluate_platoon_and_arsenal(p1, switch_batter)
    assert plan.batter_side == 'L'
    assert plan.platoon_advantage == 'BATTER'


def test_evaluate_platoon_opposite_handed_offspeed_boost():
    p1 = get_player(1)  # RHP
    lhb = {
        'name': 'Lefty Batter',
        'id': 100,
        'vitals': {'bats': 'L', 'handedness': 'L'},
    }
    arsenal_data = [
        {'name': '4-Seam Fastball', 'category': 'FASTBALL', 'usage_pct': 0.40},
        {'name': 'Changeup', 'category': 'OFFSPEED', 'usage_pct': 0.20},
        {'name': 'Sweeper', 'category': 'BREAKING', 'usage_pct': 0.30},
    ]
    pitcher = {
        'name': 'Test Pitcher',
        'id': 50,
        'vitals': {'throws': 'R'},
        'pitch_arsenal': arsenal_data,
    }
    plan = evaluate_platoon_and_arsenal(pitcher, lhb)
    assert plan.platoon_advantage == 'BATTER'
    # Changeup should receive opposite-hand boost, Sweeper should be discounted vs opposite hand
    assert plan.pitch_base_weights['Changeup'] > 0.20
    assert plan.pitch_base_weights['Sweeper'] < 0.30

