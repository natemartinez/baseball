"""
Tests verifying the team selection bridge in routes.py and GameEngine decoupling.
"""

from backend.api.app import create_app
from backend.engine.game_engine.engine import GameEngine


def test_game_engine_decoupled_team_names():
    """Verify GameEngine defaults team names from roster dicts instead of hardcoded strings."""
    home_roster = {"team_name": "Boston Red Sox", "position_players": [], "pitchers": {"starters": []}}
    away_roster = {"team_name": "Chicago Cubs", "position_players": [], "pitchers": {"starters": []}}

    engine = GameEngine(home_roster, away_roster)
    assert engine.home_name == "Boston Red Sox"
    assert engine.away_name == "Chicago Cubs"
    assert "Boston Red Sox" in engine.score
    assert "Chicago Cubs" in engine.score


def test_api_teams_with_and_without_players():
    """Verify /api/teams returns basic metadata by default and full rosters when requested."""
    app = create_app()
    client = app.test_client()

    # 1. Default teams query
    res = client.get("/api/teams")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert len(data["teams"]) >= 2
    assert "position_players" not in data["teams"][0]

    # 2. Query with include_players=true
    res_players = client.get("/api/teams?include_players=true")
    assert res_players.status_code == 200
    data_players = res_players.get_json()
    assert data_players["status"] == "ok"
    team0 = data_players["teams"][0]
    assert "position_players" in team0
    assert len(team0["position_players"]) > 0
    assert "pitchers" in team0
    assert len(team0["pitchers"]["starters"]) > 0


def test_api_teams_selection_endpoint():
    """Verify dedicated /api/teams/selection bridge endpoint."""
    app = create_app()
    client = app.test_client()

    res = client.get("/api/teams/selection")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert len(data["teams"]) >= 2
    for team in data["teams"]:
        assert "id" in team
        assert "name" in team
        assert "position_players" in team
        assert "pitchers" in team
        assert len(team["position_players"]) > 0


def test_start_game_with_custom_team_selection():
    """Verify starting game with chosen home and away team IDs."""
    app = create_app()
    client = app.test_client()

    # Start game with Yankees (id 2) as Home and Mets (id 1) as Away
    res = client.post("/api/start_game", json={"home_team_id": 2, "away_team_id": 1, "seed": 42})
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["home_team"] == "New York Yankees"
    assert payload["away_team"] == "New York Mets"

    # Verify state reflects this selection
    state_res = client.get("/api/state")
    assert state_res.status_code == 200
    state = state_res.get_json()
    assert state["teams"] == ["New York Yankees", "New York Mets"]
    assert state["lineups"][0]["team_name"] == "New York Yankees"
    assert state["lineups"][1]["team_name"] == "New York Mets"
