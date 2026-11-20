"""
Unit tests for backend.database.roster_store.RosterStore.
"""

import pytest
from backend.database.roster_store import RosterStore, roster_store


@pytest.fixture(autouse=True)
def clean_store():
    """Ensure a clean, warmed store for each test."""
    roster_store.clear()
    roster_store.warmup(season=2026)
    yield
    roster_store.clear()


def test_roster_store_warmup_and_teams():
    """Verify that warmup loads all teams and indexes them by ID, name, and abbreviation."""
    teams = roster_store.get_all_teams()
    assert len(teams) >= 2

    # Lookup by int ID
    t1 = roster_store.get_team(1)
    assert t1 is not None
    assert "name" in t1

    # Lookup by string ID
    assert roster_store.get_team("1") == t1

    # Lookup by name (case-insensitive)
    t_name = roster_store.get_team("New York Yankees")
    assert t_name is not None
    assert roster_store.get_team("new york yankees") == t_name

    # Lookup by abbreviation (case-insensitive)
    t_abbr = roster_store.get_team("NYY")
    assert t_abbr == t_name
    assert roster_store.get_team("nyy") == t_name


def test_roster_store_get_roster_categorization():
    """Verify that get_roster returns exact structure with position players, starters, and bullpen."""
    roster = roster_store.get_roster("New York Yankees", season=2026)
    assert roster is not None
    assert "team_id" in roster
    assert "team_name" in roster
    assert "position_players" in roster
    assert "pitchers" in roster
    assert "starters" in roster["pitchers"]
    assert "bullpen" in roster["pitchers"]

    # Enriched 40-man roster structure: full lineup, 5-man rotation, and active bullpen
    assert len(roster["position_players"]) >= 9
    assert len(roster["pitchers"]["starters"]) == 5
    assert len(roster["pitchers"]["bullpen"]) >= 5

    # Check Mets roster structure
    mets = roster_store.get_roster("New York Mets", season=2026)
    assert mets is not None
    assert len(mets["position_players"]) >= 9
    assert len(mets["pitchers"]["starters"]) == 5
    assert len(mets["pitchers"]["bullpen"]) >= 5


def test_roster_store_safe_cloning():
    """Verify that get_roster(clone=True) protects in-memory templates from in-game mutation."""
    roster1 = roster_store.get_roster("New York Yankees", season=2026, clone=True)
    p1 = roster1["position_players"][0]
    orig_order = getattr(p1, "batting_order", None)

    # Mutate player in roster1
    p1.batting_order = 999
    # Mutate list order
    roster1["position_players"].reverse()

    # Fetch a fresh copy
    roster2 = roster_store.get_roster("New York Yankees", season=2026, clone=True)
    fresh_p1 = roster2["position_players"][0]

    assert getattr(fresh_p1, "batting_order", None) == orig_order
    assert fresh_p1.name != roster1["position_players"][0].name or orig_order != 999


def test_roster_store_get_player_and_legacy_fallback():
    """Verify direct player lookup by ID with legacy alias mapping support."""
    # Authoritative ID: Aaron Judge (201)
    judge = roster_store.get_player(201, season=2026)
    assert judge is not None
    assert judge.name == "Aaron Judge"

    # Legacy ID: 2 maps to 201
    judge_legacy = roster_store.get_player(2, season=2026)
    assert judge_legacy is not None
    assert judge_legacy.name == "Aaron Judge"
    assert judge_legacy.id == 201

    # Nolan McLean: 101, legacy 1
    mclean = roster_store.get_player(101, season=2026)
    assert mclean is not None
    assert mclean.name == "Nolan McLean"
    mclean_legacy = roster_store.get_player(1, season=2026)
    assert mclean_legacy is not None
    assert mclean_legacy.name == "Nolan McLean"

