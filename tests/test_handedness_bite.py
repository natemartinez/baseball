"""Handedness convention tests for release slots, command miss, and pitch bite.

Canonical convention:
- +X is the first-base side (catcher's right).
- RHP release is negative X; LHP release is positive X.
- Early misses sail high and arm-side: -X for RHP, +X for LHP.
- Arsenal horizontal break stays RHP-normalized (positive = glove side).
"""

import random

from backend.database.db import get_player
from backend.engine.game_engine.gameday_math import sample_directional_dispersion
from backend.models.player import Player
from tiers import TimingTier


def test_player_default_release_x_is_arm_side():
    righty = Player("Righty", throws="R", position="P")
    lefty = Player("Lefty", throws="L", position="P")

    assert righty.release_point_ft["x"] < 0
    assert lefty.release_point_ft["x"] > 0


def test_early_miss_is_arm_side_for_each_hand():
    rng = random.Random(20261102)
    for hand, expected_sign in (("R", -1), ("L", 1)):
        for _ in range(200):
            dx, dz, _ = sample_directional_dispersion(
                executed_radius_inches=4.0,
                timing_tier=TimingTier.OKAY,
                pitcher_hand=hand,
                timing_label="EARLY • OKAY",
                rng=rng,
            )
            assert dz > 0
            assert dx * expected_sign > 0


def test_seeded_pitchers_use_arm_side_release_points():
    for pitcher_id in (101, 401, 102):
        pitcher = get_player(pitcher_id)
        assert pitcher is not None
        assert pitcher.throws == "R"
        assert pitcher.release_point_ft["x"] < 0

    manaea = get_player(103)
    assert manaea is not None
    assert manaea.name == "Sean Manaea"
    assert manaea.throws == "L"
    assert manaea.release_point_ft["x"] > 0


def test_lhp_arsenal_keeps_rhp_normalized_break_signs():
    manaea = get_player(103)
    assert manaea is not None

    arsenal = {pitch["id"]: pitch for pitch in manaea.pitch_arsenal}
    assert arsenal["SWP"]["horizontal_break_in"] > 0
    assert arsenal["SL"]["horizontal_break_in"] > 0
    assert arsenal["CH"]["horizontal_break_in"] < 0
    assert arsenal["SI"]["horizontal_break_in"] < 0


def test_gameday_packet_release_matches_lhp_hand():
    from backend.engine.game_engine import GameEngine

    manaea = get_player(103)
    judge = get_player(201)
    assert manaea is not None and judge is not None

    home_roster = {
        "team_id": 1,
        "team_name": "New York Mets",
        "position_players": [judge],
        "pitchers": {"starters": [manaea], "bullpen": []},
    }
    away_roster = {
        "team_id": 2,
        "team_name": "New York Yankees",
        "position_players": [judge],
        "pitchers": {"starters": [manaea], "bullpen": []},
    }

    engine = GameEngine(
        home_roster,
        away_roster,
        "New York Mets",
        "New York Yankees",
        seed=42,
    )
    packet = engine.throw_pitch(selection_mode="user", pitch_name="Sweeper")

    assert packet["status"] == "success"
    gameday = packet["pitch_details"]["gameday_packet"]
    release = gameday["release"]
    assert release["x"] > 0
    assert gameday["meta"]["pitcherHand"] == "L"
    # Raw packet break stays RHP-normalized; the renderer mirrors it for LHP.
    assert gameday["execution"]["horizontalBreakInches"] > 0
    shape = gameday["execution"]["shape"]
    assert shape["verticalApproachAngleDeg"] < 0
    assert isinstance(shape["verticalOffsetInches"], float)
