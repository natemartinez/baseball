from backend.database.db import get_player
from backend.engine.game_engine.engine import GameEngine
from backend.engine.pitching_engine.pitcher_info import ActivePitcherState
from backend.models.player import Player

def _make_game():
    p1 = get_player(1)
    p2 = get_player(2)
    mclean = p1 if p1 and p1.is_pitcher else p2
    judge = p2 if p1 and p1.is_pitcher else p1

    home_team = {
        "name": "New York Mets",
        "position_players": [judge],
        "pitchers": {"starters": [mclean], "bullpen": []},
    }
    away_team = {
        "name": "New York Yankees",
        "position_players": [judge],
        "pitchers": {"starters": [mclean], "bullpen": []},
    }
    return GameEngine(home_team, away_team, "Mets", "Yankees")

def test_game_engine_maintains_active_pitcher_states():
    game = _make_game()
    # Check that ActivePitcherState instances are created and tracked
    assert game.home_pitcher_state is not None
    assert game.away_pitcher_state is not None
    assert isinstance(game.home_pitcher_state, ActivePitcherState)
    assert isinstance(game.away_pitcher_state, ActivePitcherState)

    # In TOP of 1st, home pitcher is pitching
    assert game.top_bottom == 'TOP'
    current_state = game.current_pitcher_state()
    assert current_state is game.home_pitcher_state

    # Switch half inning
    game._switch_half_inning()
    assert game.top_bottom in ('BOTTOM', 'BOT')
    assert game.current_pitcher_state() is game.away_pitcher_state


def test_build_arsenal_payload_uses_cached_metrics():
    game = _make_game()
    payload = game.build_pitcher_arsenal_payload()
    assert isinstance(payload, list)
    assert len(payload) > 0
    # Payload items include velocity, spin, and command
    assert "name" in payload[0]
