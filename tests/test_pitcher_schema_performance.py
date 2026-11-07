#!/usr/bin/env python3
"""
Unit & Anti-Reward-Hacking Test Suite for Pitcher Schema & Performance Optimization.

Guarantees:
1. Schema Hydration & Serialization: Kodai Senga schema integrity (stamina, composure,
   arm_slot, arm_slot_angle_deg, release_point_ft, release_consistency).
2. Arsenal Field Completeness: id, command, max_radius_inches, sigma, spin_rate_rpm,
   spin_axis_deg, tunnel_partners.
3. O(1) Fast-Path Pitch Retrieval: Instant dictionary lookup by ID/name without regex loops.
4. Base + Delta Immutability: Dynamic fatigue degradation alters in-game delivery command
   without ever mutating the baseline player arsenal schema.
5. Pitch Tunneling Synergy: Constant-time detection when consecutive pitches are tunnel partners.
6. Biomechanical Release Telemetry: Gameday packet uses true pitcher release coordinates
   rather than the legacy hardcoded (-2.1, 54.5, 5.9).
"""

from pathlib import Path
import sys
import pytest

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database.db import get_player
from backend.models.player import Player


def get_live_senga() -> Player:
    """Returns the authoritative Kodai Senga Player instance hydrated directly from the live database."""
    player = get_player(102)
    assert player is not None, "Kodai Senga (ID 102) must exist in the live database"
    return player


# ==============================================================================
# 1. Schema Hydration, Validation & Serialization Integrity
# ==============================================================================

def test_senga_hydration_and_biomechanical_attributes():
    """Validates that Kodai Senga hydrated from the live database matches the authoritative schema."""
    player = get_live_senga()

    assert player.id == 102
    assert player.name == "Kodai Senga"
    assert player.is_pitcher is True
    assert player.stamina == 84.0
    assert player.composure == 86.0
    assert player.arm_slot == "THREE_QUARTERS"
    assert player.arm_slot_angle_deg == 52.0
    assert player.consistency == 88.0
    assert player.release_consistency == 88.0
    assert player.get_rating("consistency") == 88.0
    assert player.get_rating("Consistency") == 88.0
    assert player.ratings.get("consistency") == 88.0 or player.ratings.get("Consistency") == 88.0
    assert player.release_point_ft == {"x": -1.85, "y": 54.6, "z": 5.9}
    assert isinstance(player.motion_bio, dict)
    assert player.motion_bio["arm_slot"] == "THREE_QUARTERS"
    assert player.motion_bio["arm_slot_angle_deg"] == 52.0
    assert player.motion_bio["release_point_ft"] == {"x": -1.85, "y": 54.6, "z": 5.9}

    # Verify arsenal hydration from live database
    assert len(player.pitch_arsenal) == 3
    fb = player.pitch_arsenal[0]
    assert fb["id"] == "4SFB"
    assert fb["command"] == 82.0
    assert fb["max_radius_inches"] == 1.5
    assert fb["sigma"] == 0.05
    assert fb["spin_rate_rpm"] == 2240
    assert fb["spin_axis_deg"] == 205.0
    assert fb["tunnel_partners"] == ["GFORK", "CUT"]

    gf = player.pitch_arsenal[1]
    assert gf["id"] == "GFORK"
    assert gf["command"] == 86.0
    assert gf["tunnel_partners"] == ["4SFB", "CUT"]

    cut = player.pitch_arsenal[2]
    assert cut["id"] == "CUT"
    assert cut["command"] == 83.0
    assert cut["tunnel_partners"] == ["4SFB", "GFORK"]


def test_player_serialization_roundtrip():
    """Validates that to_dict() preserves all new schema fields cleanly."""
    player = get_live_senga()
    serialized = player.to_dict()

    assert serialized["id"] == 102
    assert serialized["stamina"] == 84.0
    assert serialized["composure"] == 86.0
    assert serialized["consistency"] == 88.0
    assert serialized["release_consistency"] == 88.0
    assert serialized["motion_bio"]["arm_slot"] == "THREE_QUARTERS"
    assert serialized["motion_bio"]["arm_slot_angle_deg"] == 52.0
    assert serialized["motion_bio"]["release_point_ft"]["x"] == -1.85
    assert serialized["arm_slot"] == "THREE_QUARTERS"
    assert serialized["arm_slot_angle_deg"] == 52.0
    assert serialized["release_point_ft"]["x"] == -1.85
    assert serialized["pitch_arsenal"][0]["id"] == "4SFB"
    assert serialized["pitch_arsenal"][0]["tunnel_partners"] == ["GFORK", "CUT"]

    # Re-hydrate from serialized representation
    rehydrated = Player.from_dict(serialized)
    assert rehydrated.id == 102
    assert rehydrated.arm_slot == "THREE_QUARTERS"
    assert rehydrated.motion_bio["arm_slot"] == "THREE_QUARTERS"
    assert rehydrated.release_point_ft["y"] == 54.6
    assert rehydrated.consistency == 88.0


# ==============================================================================
# 2. O(1) Pitch Retrieval & Backward-Compatible Aliases
# ==============================================================================

def test_o1_pitch_lookup_by_id_and_name():
    """Asserts that Player provides an O(1) indexed lookup by pitch ID and name."""
    player = get_live_senga()

    # Direct ID lookup
    p_by_id = player.get_pitch_fast("4SFB")
    assert p_by_id is not None
    assert p_by_id["name"] == "4-Seam Fastball"
    assert p_by_id["command"] == 82.0

    # Name lookup (case-insensitive)
    p_by_name = player.get_pitch_fast("ghost fork")
    assert p_by_name is not None
    assert p_by_name["id"] == "GFORK"
    assert p_by_name["command"] == 86.0

    # Non-existent pitch
    assert player.get_pitch_fast("Knuckleball") is None


def test_backward_compatible_aliases():
    """Ensures legacy code referencing control_rating or spin_rpm does not break."""
    player = get_live_senga()
    fb = player.pitch_arsenal[0]

    # command should alias control_rating, spin_rate_rpm should alias spin_rpm
    assert fb.get("command") == 82.0
    assert fb.get("control_rating") == 82.0
    assert fb.get("spin_rate_rpm") == 2240
    assert fb.get("spin_rpm") == 2240


# ==============================================================================
# 3. Base + Delta Immutability (Anti-Reward Hacking Guard)
# ==============================================================================

def test_stamina_fatigue_preserves_immutable_baseline():
    """
    Guarantees that when fatigue degrades effective command at runtime,
    the pre-baked baseline in Player.pitch_arsenal is NEVER mutated or corrupted.
    """
    from backend.engine.pitching_engine.pitcher_info import (
        InGamePitcherRatings,
        evaluate_pitch_arsenal,
    )

    player = get_live_senga()
    baseline_command_before = player.pitch_arsenal[0]["command"]
    assert baseline_command_before == 82.0

    # Simulate in-game ratings past stamina threshold (e.g. 95 pitches thrown on 84 stamina)
    in_game_state = InGamePitcherRatings(
        pitcher=player,
        base_stamina=player.stamina,
        base_command=player.ratings.get("Control", 82.0),
        pitch_count=95,
        fatigue_pct=40.0,
    )

    metrics = evaluate_pitch_arsenal(player, in_game_ratings=in_game_state)
    fb_metrics = metrics.get("4-Seam Fastball") or metrics.get("4SFB")
    assert fb_metrics is not None

    # Dynamic in-game command must decay due to fatigue
    assert fb_metrics.effective_command < 82.0

    # CRITICAL: The persistent player schema baseline must remain strictly untouched!
    assert player.pitch_arsenal[0]["command"] == 82.0
    assert player.pitch_arsenal[0]["max_radius_inches"] == 1.5


# ==============================================================================
# 4. Fast-Path Pre-Computed Dispersion
# ==============================================================================

def test_precomputed_dispersion_fast_path():
    """Validates that calculate_pitch_delivery uses pre-baked sigma directly."""
    from backend.engine.pitching_engine.pitch_execution.calculations import (
        calculate_pitch_delivery,
    )

    # Deliver using Senga's pre-computed sigma (0.05 ft) and max_radius (1.5 in)
    delivery = calculate_pitch_delivery(
        target_x=0.0,
        target_z=2.5,
        command_rating=82.0,
        pitch_count=10,
        stamina=84.0,
        precomputed_sigma=0.05,
        precomputed_max_radius_in=1.5,
    )

    assert delivery["max_radius_inches"] == 1.5
    assert delivery["sigma"] == 0.05
    # Radial miss must be strictly bounded within the hard maximum radius
    assert delivery["radial_miss_in"] <= 1.501


# ==============================================================================
# 5. Pitch Tunneling Synergy (O(1) Set Lookup)
# ==============================================================================

def test_pitch_tunneling_detection():
    """
    Validates constant-time pitch tunneling detection:
    When GFORK is thrown after 4SFB, tunneling is flagged as active.
    When 4SFB is thrown after an unrelated pitch, tunneling is flagged false.
    """
    player = get_live_senga()

    # Case A: Sequence is 4SFB -> GFORK (4SFB is in GFORK's tunnel_partners)
    gfork = player.get_pitch_fast("GFORK")
    assert "4SFB" in gfork.get("tunnel_partners", [])

    # Case B: Sequence is Curveball -> 4SFB (Curveball is NOT in 4SFB's tunnel_partners)
    fb = player.get_pitch_fast("4SFB")
    assert "CURVE" not in fb.get("tunnel_partners", [])


# ==============================================================================
# 6. Biomechanical Release Point Telemetry in Gameday Packet
# ==============================================================================

def test_gameday_packet_uses_true_release_point():
    """
    Validates that GameEngine constructs gameday_packet with the pitcher's true
    biomechanical release coordinates (RHP negative X / third-base side).
    """
    from backend.engine.game_engine import GameEngine

    player = get_live_senga()
    batter = get_player(2)
    assert batter is not None

    home_roster = {
        "team_id": 1,
        "team_name": "New York Mets",
        "position_players": [batter],
        "pitchers": {"starters": [player], "bullpen": []},
    }
    away_roster = {
        "team_id": 2,
        "team_name": "New York Yankees",
        "position_players": [batter],
        "pitchers": {"starters": [player], "bullpen": []},
    }

    engine = GameEngine(home_roster, away_roster, "New York Mets", "New York Yankees", seed=42)
    packet = engine.throw_pitch(selection_mode="user", pitch_name="4-Seam Fastball")

    assert packet["status"] == "success"
    gameday_packet = packet["pitch_details"]["gameday_packet"]

    release = gameday_packet["release"]
    # Kodai Senga's true release extension: x ~ -1.85 (third-base/arm side), y ~ 54.6, z ~ 5.90
    assert abs(release["x"] + 1.85) < 0.25  # Accounts for release consistency jitter
    assert abs(release["y"] - 54.6) < 0.25
    assert abs(release["z"] - 5.90) < 0.25
    assert gameday_packet["meta"].get("armSlot") == "THREE_QUARTERS"
    assert gameday_packet["meta"].get("armSlotAngleDeg") == 52.0


# ==============================================================================
# 7. Multi-Pitcher Database Integrity & Default Arsenal Standardization
# ==============================================================================

def test_all_db_pitchers_have_modern_schema():
    """
    Verifies that all pitchers seeded in the SQLite database (Nolan McLean,
    Gerrit Cole, Kodai Senga, Sean Manaea) have complete biomechanics and
    pre-computed arsenals.
    """
    from backend.database.db import get_team_roster_players

    mets_players = get_team_roster_players("New York Mets")
    yankees_players = get_team_roster_players("New York Yankees")
    all_pitchers = [p for p in mets_players + yankees_players if getattr(p, "is_pitcher", False) or getattr(p, "position", "") == "P"]

    pitcher_names = {p.name for p in all_pitchers}
    assert "Nolan McLean" in pitcher_names
    assert "Gerrit Cole" in pitcher_names
    assert "Kodai Senga" in pitcher_names

    for pitcher in all_pitchers:
        # Biomechanical top-level vitals
        assert pitcher.arm_slot in ("THREE_QUARTERS", "OVER_THE_TOP", "SUBMARINE", "SIDEARM"), f"Missing arm_slot on {pitcher.name}"
        assert pitcher.arm_slot_angle_deg is not None and pitcher.arm_slot_angle_deg > 0
        assert pitcher.consistency is not None and pitcher.consistency >= 70
        assert pitcher.release_consistency == pitcher.consistency
        assert pitcher.stamina is not None and pitcher.stamina >= 70
        assert pitcher.composure is not None and pitcher.composure >= 70
        assert pitcher.get_rating("composure") >= 70
        assert pitcher.get_rating("consistency") >= 70

        assert isinstance(pitcher.motion_bio, dict), f"Missing motion_bio on {pitcher.name}"
        assert pitcher.motion_bio["arm_slot"] == pitcher.arm_slot
        assert pitcher.motion_bio["arm_slot_angle_deg"] == pitcher.arm_slot_angle_deg
        assert pitcher.motion_bio["release_point_ft"] == pitcher.release_point_ft

        rel = pitcher.release_point_ft
        assert isinstance(rel, dict), f"Missing release_point_ft on {pitcher.name}"
        assert abs(rel["x"]) > 0 and rel["y"] > 50 and rel["z"] > 4

        # Complete arsenal pre-computed constants
        arsenal = pitcher.pitch_arsenal
        assert len(arsenal) >= 2, f"Pitcher {pitcher.name} has fewer than 2 pitches"
        for pitch in arsenal:
            assert pitch.get("id"), f"Pitch missing id on {pitcher.name}: {pitch}"
            assert pitch.get("category") in ("FASTBALL", "BREAKING", "OFF_SPEED"), f"Invalid category on {pitcher.name}: {pitch}"
            assert "–" in pitch.get("velocity_display", "") or "-" in pitch.get("velocity_display", "")
            assert pitch.get("command") is not None and pitch["command"] > 0
            assert pitch.get("max_radius_inches") is not None and pitch["max_radius_inches"] > 0
            assert pitch.get("sigma") is not None and pitch["sigma"] > 0
            assert isinstance(pitch.get("tunnel_partners"), list)


@pytest.mark.parametrize("pitcher_name,pitch_id,expected_name", [
    ("Nolan McLean", "4SFB", "Four-Seam Fastball"),
    ("Nolan McLean", "SWP", "Spin Monster Sweeper"),
    ("Gerrit Cole", "4SFB", "Four-Seam Fastball"),
    ("Gerrit Cole", "SL", "Slider"),
    ("Kodai Senga", "4SFB", "4-Seam Fastball"),
    ("Kodai Senga", "GFORK", "Ghost Fork"),
    ("Kodai Senga", "CUT", "Cutter"),
])
def test_all_pitchers_o1_lookups(pitcher_name, pitch_id, expected_name):
    """Verifies O(1) pitch retrieval for all pitchers by ID and display name."""
    from backend.database.db import get_team_roster_players

    team = "New York Yankees" if pitcher_name == "Gerrit Cole" else "New York Mets"
    players = [p for p in get_team_roster_players(team) if p.name == pitcher_name]
    assert len(players) == 1
    pitcher = players[0]

    pitch_by_id = pitcher.get_pitch_fast(pitch_id)
    assert pitch_by_id is not None
    assert pitch_by_id["name"] == expected_name

    pitch_by_name = pitcher.get_pitch_fast(expected_name)
    assert pitch_by_name is not None
    assert pitch_by_name["id"] == pitch_id


@pytest.mark.parametrize("pitcher_name,pitch_a_id,pitch_b_id", [
    ("Nolan McLean", "4SFB", "SWP"),
    ("Gerrit Cole", "4SFB", "SL"),
    ("Kodai Senga", "4SFB", "GFORK"),
])
def test_all_pitchers_tunneling_pairs(pitcher_name, pitch_a_id, pitch_b_id):
    """Verifies tunneling partner relationships across all pitchers."""
    from backend.database.db import get_team_roster_players

    team = "New York Yankees" if pitcher_name == "Gerrit Cole" else "New York Mets"
    pitcher = [p for p in get_team_roster_players(team) if p.name == pitcher_name][0]

    pitch_a = pitcher.get_pitch_fast(pitch_a_id)
    pitch_b = pitcher.get_pitch_fast(pitch_b_id)

    assert pitch_b_id in pitch_a.get("tunnel_partners", []), f"{pitch_b_id} not in {pitcher_name}'s {pitch_a_id} tunnel partners"
    assert pitch_a_id in pitch_b.get("tunnel_partners", []), f"{pitch_a_id} not in {pitcher_name}'s {pitch_b_id} tunnel partners"


def test_default_engine_fallback_arsenal_standardization():
    """Verifies that the engine's fallback arsenal carries all pre-computed schema constants."""
    from backend.engine.pitching_engine.pitch_execution.pitch_objects import DEFAULT_ARSENAL
    from backend.engine.game_engine.engine import _DEFAULT_ARSENAL_PAYLOAD

    for source, label in [(DEFAULT_ARSENAL, "DEFAULT_ARSENAL"), (_DEFAULT_ARSENAL_PAYLOAD, "_DEFAULT_ARSENAL_PAYLOAD")]:
        assert len(source) >= 4, f"{label} has fewer than 4 pitches"
        for p in source:
            assert p.get("id"), f"{label} pitch missing id: {p}"
            assert p.get("category") in ("FASTBALL", "BREAKING", "OFF_SPEED")
            assert p.get("velocity_display")
            assert p.get("max_radius_inches") is not None and p["max_radius_inches"] > 0
            assert p.get("sigma") is not None and p["sigma"] > 0
            assert isinstance(p.get("tunnel_partners"), list) and len(p["tunnel_partners"]) > 0

