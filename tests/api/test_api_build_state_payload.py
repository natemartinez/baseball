"""
Unit tests verifying that _build_state_payload does not call get_all_teams()
or perform unnecessary full-database team/roster lookups during game state queries.
"""

from unittest.mock import patch
from backend.api.app import create_app
from backend.api.routes import _build_state_payload, load_team_roster
from backend.engine.game_engine.engine import GameEngine


def test_build_state_payload_never_calls_get_all_teams():
    """Verify that calling _build_state_payload directly with an engine never invokes get_all_teams."""
    home_roster = load_team_roster(1)
    away_roster = load_team_roster(2)
    engine = GameEngine(
        home_roster,
        away_roster,
        home_name="Home Team",
        away_name="Away Team",
        seed=123,
    )

    with patch("backend.api.routes.get_all_teams") as mock_get_all_teams:
        mock_get_all_teams.side_effect = AssertionError("get_all_teams() was called inside _build_state_payload!")

        payload = _build_state_payload(engine=engine)

        mock_get_all_teams.assert_not_called()
        assert len(payload["teams"]) == 2
        assert payload["teams"] == ["Home Team", "Away Team"]
        assert len(payload["lineups"]) == 2
        assert len(payload["rotations"]) == 2
        assert payload["game"] is not None
        assert payload["game_state"] is not None


def test_api_state_endpoint_never_calls_get_all_teams_when_active():
    """Verify that GET /api/state does not call get_all_teams once an active game exists."""
    app = create_app()
    client = app.test_client()

    # Initialize the game via start_game
    res = client.post("/api/start_game", json={"home_team_id": 1, "away_team_id": 2})
    assert res.status_code == 200

    with patch("backend.api.routes.get_all_teams") as mock_get_all_teams:
        mock_get_all_teams.side_effect = AssertionError("get_all_teams() was called during GET /api/state!")

        state_res = client.get("/api/state")
        assert state_res.status_code == 200
        mock_get_all_teams.assert_not_called()

        data = state_res.get_json()
        assert len(data["teams"]) == 2
        assert len(data["lineups"]) == 2
        assert len(data["rotations"]) == 2
