import pytest
from backend.database.db import get_player
from backend.engine.pitching_engine.pitcher_info import ActivePitcherState


def test_active_pitcher_prebakes_lineup_game_plan():
    p1 = get_player(1)  # Pitcher
    p2 = get_player(2)  # Batter
    state = ActivePitcherState.from_player(p1)

    assert state.game_plan == {}
    lineup = [p2, {'name': 'Rookie', 'id': 105, 'bats': 'L'}]
    state.prebake_lineup_game_plan(lineup)

    assert len(state.game_plan) == 2
    plan_judge = state.get_matchup_plan(p2)
    assert plan_judge.batter_name == p2.name

    # Lazy fallback for unexpected batter
    pinch_hitter = {'name': 'Pinch Hitter', 'id': 200, 'bats': 'R'}
    plan_ph = state.get_matchup_plan(pinch_hitter)
    assert plan_ph.batter_name == 'Pinch Hitter'
    assert 200 in state.game_plan


def test_active_pitcher_records_at_bat_history():
    p1 = get_player(1)
    p2 = get_player(2)
    state = ActivePitcherState.from_player(p1)

    state.record_at_bat_pitch(p2, '4-Seam Fastball')
    state.record_at_bat_pitch(p2, 'Spin Monster Sweeper')

    history = state.at_bat_history.get(p2.id or p2.name)
    assert history == ['4-Seam Fastball', 'Spin Monster Sweeper']

