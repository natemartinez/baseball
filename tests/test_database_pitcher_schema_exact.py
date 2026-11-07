#!/usr/bin/env python3
"""
Unit Test Suite: Database Pitcher Schema Exact Parity with Authoritative Seed Data.

Validates that backend/database (SQLite storage, queries, and _row_to_dict)
matches the pitcher JSON schema seen in backend/database/seed_data.json exactly,
key-for-key, type-for-type, and value-for-value.
"""

import json
from pathlib import Path
import sys
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database.db import get_player, get_team_roster, init_db
from backend.models.player import Player

SEED_DATA_PATH = ROOT_DIR / "backend" / "database" / "seed_data.json"


@pytest.fixture(scope="module")
def seed_pitchers():
    """Loads all pitchers directly from the seed database JSON."""
    with open(SEED_DATA_PATH, "r") as f:
        data = json.load(f)
    pitchers = [
        p for p in data.get("players", [])
        if p.get("position") in ("P", "SP", "RP", "CP") or p.get("role") in ("pitcher", "starter")
    ]
    assert len(pitchers) == 4, f"Expected 4 pitchers in seed DB, found {len(pitchers)}"
    return pitchers


def test_database_pitcher_schema_exact_parity(seed_pitchers):
    """
    Validates that every pitcher in the database matches the seed database
    representation for all 13 top-level keys and nested objects.
    """
    mets_roster = {p["id"]: p for p in get_team_roster("New York Mets")}
    yankees_roster = {p["id"]: p for p in get_team_roster("New York Yankees")}
    db_players = {**mets_roster, **yankees_roster}

    required_keys = [
        "id", "name", "team", "position", "role", "jersey_number",
        "throws", "bats", "motion_bio", "ratings", "arsenal",
        "season_stats", "live_game_stats"
    ]

    for seed_p in seed_pitchers:
        pid = seed_p["id"]
        assert pid in db_players, f"Pitcher {seed_p['name']} (ID {pid}) not found in DB roster"
        db_p = db_players[pid]

        # 1. Verify every required key exists and matches
        for k in required_keys:
            assert k in db_p, f"Missing key '{k}' in DB pitcher {seed_p['name']}"
            seed_val = seed_p[k]
            db_val = db_p[k]

            # Deep compare dicts and lists
            assert db_val == seed_val, (
                f"Mismatch for pitcher '{seed_p['name']}' on field '{k}':\n"
                f"  Seed: {seed_val}\n"
                f"  DB:   {db_val}"
            )

        # 2. Verify types match
        assert isinstance(db_p["id"], int)
        assert isinstance(db_p["name"], str)
        assert isinstance(db_p["team"], str)
        assert isinstance(db_p["position"], str)
        assert isinstance(db_p["role"], str)
        assert isinstance(db_p["jersey_number"], int)
        assert isinstance(db_p["throws"], str)
        assert isinstance(db_p["bats"], str)
        assert isinstance(db_p["motion_bio"], dict)
        assert isinstance(db_p["ratings"], dict)
        assert isinstance(db_p["arsenal"], list)
        assert isinstance(db_p["season_stats"], dict)
        assert isinstance(db_p["live_game_stats"], dict)

        # 3. Verify arsenal pitch fields
        for seed_pitch, db_pitch in zip(seed_p["arsenal"], db_p["arsenal"]):
            assert db_pitch == seed_pitch, (
                f"Arsenal mismatch for pitch '{seed_pitch.get('name')}' in {seed_p['name']}:\n"
                f"  Seed: {seed_pitch}\n"
                f"  DB:   {db_pitch}"
            )


def test_pitcher_hydration_and_statcast_rating_aliases():
    """Validates that Player correctly hydrates and aliases Statcast rating keys."""
    mclean = get_player(101)
    assert mclean is not None
    assert mclean.id == 101
    assert mclean.name == "Nolan McLean"
    assert mclean.is_pitcher is True
    assert mclean.jersey_number == 56
    assert mclean.throws == "R"
    assert mclean.bats == "R"

    # Statcast rating key aliasing
    assert mclean.get_rating("Velocity") == 98.0
    assert mclean.get_rating("velocity_rating") == 98.0
    assert mclean.get_rating("Break") == 94.0
    assert mclean.get_rating("break_rating") == 94.0
    assert mclean.get_rating("Arm Strength") == 97.0
    assert mclean.get_rating("arm_strength") == 97.0
    assert mclean.get_rating("Control") == 82.0
    assert mclean.get_rating("control") == 82.0
    assert mclean.get_rating("Stamina") == 88.0
    assert mclean.get_rating("stamina") == 88.0
    assert mclean.get_rating("Composure") == 80.0
    assert mclean.get_rating("composure") == 80.0
    assert mclean.get_rating("Consistency") == 82.0
    assert mclean.get_rating("consistency") == 82.0

    # Serialization preserves schema
    serialized = mclean.to_dict()
    assert serialized["id"] == 101
    assert serialized["jersey_number"] == 56
    assert serialized["throws"] == "R"
    assert "arsenal" in serialized
    assert len(serialized["arsenal"]) == 4
    assert serialized["season_stats"]["era"] == 3.64
    assert serialized["live_game_stats"]["pitch_count"] == 18


def test_legacy_player_id_mapping():
    """Validates that legacy test IDs (1..9) resolve to the correct authoritative players."""
    p1 = get_player(1)
    assert p1 is not None and p1.name == "Nolan McLean" and p1.id == 101

    p2 = get_player(2)
    assert p2 is not None and p2.name == "Aaron Judge" and p2.id == 201

    p8 = get_player(8)
    assert p8 is not None and p8.name == "Gerrit Cole" and p8.id == 401

    p9 = get_player(9)
    assert p9 is not None and p9.name == "Kodai Senga" and p9.id == 102

