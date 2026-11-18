"""
Integration test verifying zero SQLite calls occur during live route and gameplay operations.
"""

import sqlite3
from unittest.mock import MagicMock
import pytest
from backend.api.app import create_app
from backend.database.roster_store import roster_store


def test_routes_zero_sql_during_gameplay(monkeypatch):
    """
    Verifies that after application startup warmup, no database connections or queries
    occur across teams queries, game starts, pitch execution, state inspection, lineup/rotation
    swaps, pitcher radar, or game resets.
    """
    # 1. Boot app and warm up store
    app = create_app()
    client = app.test_client()

    # 2. Spy on sqlite3.connect to count connections made during routes
    connect_calls = []
    original_connect = sqlite3.connect

    def spy_connect(*args, **kwargs):
        connect_calls.append(args)
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", spy_connect)

    # 3. Call teams endpoints
    res = client.get("/api/teams")
    assert res.status_code == 200

    res = client.get("/api/teams?include_players=true")
    assert res.status_code == 200

    res = client.get("/api/teams/selection")
    assert res.status_code == 200

    # 4. Start a game
    res = client.post("/api/start_game", json={"home_team_id": 1, "away_team_id": 2, "seed": 42})
    assert res.status_code == 200

    # 5. Fetch state
    res = client.get("/api/state")
    assert res.status_code == 200

    # 6. Execute pitch
    res = client.post("/api/pitch", json={"pitch_name": "Four-Seam Fastball", "target_zone": "heart"})
    assert res.status_code == 200

    # 7. Swap lineup and rotation
    res = client.post("/api/swap_lineup", json={"team": 1, "pos1": 1, "pos2": 2})
    assert res.status_code == 200

    res = client.post("/api/swap_rotation", json={"team": 1, "pos1": 1, "pos2": 2})
    assert res.status_code == 200

    res = client.post("/api/swap_rotation", json={"team": 2, "pos1": 1, "pos2": 2})
    assert res.status_code == 200

    # 8. Query pitcher info
    res = client.get("/api/pitcher_info?pitcher_id=101")
    assert res.status_code == 200

    # 9. Reset game
    res = client.post("/api/reset", json={"home_team_id": 1, "away_team_id": 2, "seed": 42})
    assert res.status_code == 200

    # 10. CRITICAL ASSERTION: Zero SQL calls during all operations
    assert len(connect_calls) == 0, f"Expected 0 SQLite connect calls during gameplay, found {len(connect_calls)}: {connect_calls}"
