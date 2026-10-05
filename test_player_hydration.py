#!/usr/bin/env python3
"""
Unit tests for Player Hydration & Domain Boundary Guards.
Consolidates domain entity normalization, database loading, and engine boundary contracts.
"""

from pathlib import Path
import sys

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.models.player import Player
from backend.database.db import get_player, get_team_roster_players
from backend.engine.pitching_engine import PitchingEngine
from backend.engine.game_engine import GameEngine


def test_player_hydration_and_serialization():
    """
    Consolidated Test 1: Domain Model Normalization & Serialization Roundtrip.
    Validates unflattened database lists, flattened dicts, case-insensitive ratings,
    traits, and symmetrical to_dict() / from_dict() roundtrip.
    """
    raw_db_row = {
        "id": 10,
        "name": "Test Ace",
        "number": "45",
        "position": "SP",
        "vitals": {"bats": "R", "throws": "R", "team": "New York Mets"},
        "ratings": [
            {"category": "Control", "rating": 88},
            {"category": "Stamina", "rating": 92},
            {"category": "Velocity", "rating": 97},
            {"category": "Break", "rating": 84},
        ],
        "zones": [
            {"zone": "heart", "slugging": 0.550},
            {"zone": "chase-away", "slugging": 0.120},
        ],
        "traits": [{"name": "Flame Thrower"}],
        "pitch_arsenal": [
            {"pitch": "4-Seam Fastball", "velocity_mph": 97.5, "spin_rpm": 2400, "usage_pct": 0.50},
            {"pitch": "Slider", "velocity_mph": 86.0, "spin_rpm": 2600, "usage_pct": 0.50},
        ],
    }

    # 1. Hydrate from raw DB format
    player = Player.from_dict(raw_db_row)
    assert player.id == 10
    assert player.name == "Test Ace"
    assert player.is_pitcher is True
    assert player.handedness == "R"
    assert player.get_rating("Control") == 88.0
    assert player.get_rating("control") == 88.0  # Case-insensitive lookup
    assert player.get_rating("NonExistent", default=50.0) == 50.0
    assert player.has_trait("Flame Thrower") is True
    assert player.has_trait("Unknown") is False
    assert player.zones["heart"] == 0.550

    # 2. Symmetrical Serialization Roundtrip
    p_dict = player.to_dict()
    assert p_dict["id"] == 10
    assert p_dict["ratings"]["Control"] == 88.0

    player_roundtrip = Player.from_dict(p_dict)
    assert player_roundtrip.name == player.name
    assert player_roundtrip.get_rating("Velocity") == 97.0
    assert player_roundtrip.is_pitcher is True


def test_database_hydration():
    """
    Consolidated Test 2: Database Layer Hydration.
    Validates that get_player() and get_team_roster_players() return
    canonical Player domain objects from SQLite.
    """
    # Single player lookups
    mclean = get_player(1)  # Pitcher
    judge = get_player(2)   # Batter
    assert isinstance(mclean, Player) and mclean.is_pitcher is True
    assert isinstance(judge, Player) and judge.is_pitcher is False

    # Team roster lookup
    mets_players = get_team_roster_players("New York Mets")
    assert len(mets_players) > 0
    assert all(isinstance(p, Player) for p in mets_players)


def test_engine_boundary_guards():
    """
    Consolidated Test 3: Engine Boundary Guards.
    Validates that:
      a) GameEngine auto-normalizes dictionary rosters into Player objects.
      b) PitchingEngine strictly validates participant presence (raising ValueError on None).
    """
    raw_player = {
        "id": 99,
        "name": "Roster Dict Player",
        "position": "CF",
        "number": "12",
        "ratings": {"Control": 75, "Contact": 80},
    }

    # a) GameEngine auto-conversion
    raw_roster = {
        "name": "Mets",
        "position_players": [raw_player],
        "pitchers": {"starters": [raw_player], "bullpen": []},
    }
    game = GameEngine(raw_roster, raw_roster, "Mets", "Yankees")
    assert isinstance(game.home_pitcher, Player)
    assert isinstance(game.away_pitcher, Player)
    assert isinstance(game.current_pitcher_obj(), Player)
    assert isinstance(game.current_batter_obj(), Player)

    # b) PitchingEngine strict validation
    mclean = get_player(1)
    judge = get_player(2)

    try:
        PitchingEngine(pitcher=None, batter=judge)
        assert False, "Should raise ValueError when pitcher is missing"
    except ValueError as e:
        assert "requires a pitcher object" in str(e)

    try:
        PitchingEngine(pitcher=mclean, batter=None)
        assert False, "Should raise ValueError when batter is missing"
    except ValueError as e:
        assert "requires a batter object" in str(e)


def run_all_tests():
    tests = [
        ("1. Player Hydration & Serialization Roundtrip", test_player_hydration_and_serialization),
        ("2. Database Layer Hydration (get_player & roster)", test_database_hydration),
        ("3. Engine Boundary Guards (GameEngine & PitchingEngine)", test_engine_boundary_guards),
    ]

    print("=" * 65)
    print("CONSOLIDATED TEST SUITE: Player Hydration & Boundaries")
    print("=" * 65)

    passed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            raise

    print("=" * 65)
    print(f"ALL {passed}/{len(tests)} CONSOLIDATED TESTS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    run_all_tests()

