import pytest
from backend.models.player import Player
from backend.engine.pitching_engine.pitcher_info import ActivePitcherState
from backend.engine.pitching_engine.pitcher_info.pitch_objects import PitchArsenal

def test_active_pitcher_state_from_player():
    pitcher_data = {
        "id": 42,
        "name": "Ace Starter",
        "ratings": {"Control": 85, "Stamina": 80, "Velocity": 95, "Break": 85},
        "pitch_arsenal": [
            {
                "name": "4-Seam Fastball",
                "category": "Fastball",
                "velocity_mph": 96.0,
                "spin_rpm": 2400,
                "control_rating": 85.0,
            }
        ],
    }
    player = Player.from_dict(pitcher_data)
    state = ActivePitcherState.from_player(player)

    assert state.pitcher.id == 42
    assert isinstance(state.arsenal, PitchArsenal)
    assert "4-Seam Fastball" in state.baseline_metrics
    assert state.pitch_count == 0

    # Review Focus: Verify baseline metrics immutability when fatigue increases
    initial_cmd = state.baseline_metrics["4-Seam Fastball"].effective_command
    state.pitch_count = 80
    adj_ratings = state.get_adjusted_ratings()
    assert adj_ratings.fatigue_pct > 0.0
    assert state.baseline_metrics["4-Seam Fastball"].effective_command == initial_cmd

def test_active_pitcher_state_from_dict_and_empty_arsenal():
    raw_dict = {"id": 99, "name": "Reliever", "ratings": {"Control": 70}}
    state = ActivePitcherState.from_player(raw_dict)
    assert state.pitcher.id == 99
    assert len(state.arsenal.pitches) > 0
    assert state.pitch_count == 0
    state.record_pitch("4-Seam Fastball")
    assert state.pitch_count == 1
