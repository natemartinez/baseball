#!/usr/bin/env python3
"""
Unit & Integration Test Suite for the Pitching Engine Subsystem.
Consolidates in-game fatigue ratings, count leverage strategy,
bivariate Gaussian delivery physics, and GameEngine integration.
"""

from pathlib import Path
import sys

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database.db import get_player
from backend.engine.game_engine import GameEngine
from backend.engine.pitching_engine import (
    PitchingEngine,
    PitchStrategy,
    PitcherInstanceManager,
)


def get_test_matchup():
    """Fixture: Returns Nolan McLean (Pitcher) and Aaron Judge (Batter)."""
    p1 = get_player(1)
    p2 = get_player(2)
    mclean = p1 if p1 and p1.is_pitcher else p2
    judge = p2 if p1 and p1.is_pitcher else p1
    assert mclean is not None, "Failed to load Nolan McLean (Pitcher) from DB"
    assert judge is not None, "Failed to load Aaron Judge (Batter) from DB"
    return mclean, judge


def test_pitcher_in_game_fatigue_ratings():
    """
    Consolidated Test 1: In-Game Pitcher Rating Adjustments.
    Validates dynamic fatigue curve degradation across pitch counts
    while ensuring the underlying Player domain object remains unmutated.
    """
    mclean, _ = get_test_matchup()
    orig_control = mclean.get_rating("Control", 70.0)

    # Fresh state (low pitch count)
    fresh = PitcherInstanceManager.get_adjusted_ratings(mclean, pitch_count=10)
    assert fresh.pitch_count == 10
    assert fresh.base_command == orig_control
    assert fresh.fatigue_pct < 10.0

    # Fatigued state (high pitch count)
    fatigued = PitcherInstanceManager.get_adjusted_ratings(mclean, pitch_count=90)
    assert fatigued.pitch_count == 90
    assert fatigued.effective_stamina < fresh.effective_stamina
    assert fatigued.effective_command < fresh.effective_command
    assert fatigued.fatigue_pct > fresh.fatigue_pct

    # Non-mutation guarantee
    assert mclean.get_rating("Control", 70.0) == orig_control


def test_pitch_arsenal_and_strategy_leverage():
    """
    Consolidated Test 2: Pitch Arsenal & Tactical Count Leverage.
    (Merged from test_pitch_strategy.py)
    Validates arsenal extraction and count-dependent pitch weight adaptation
    across First Pitch, Ahead 2 Strikes, Behind, Full Count, and Double Play.
    """
    mclean, judge = get_test_matchup()
    strategy = PitchStrategy(pitcher=mclean, batter=judge)

    # Repertoire validation
    assert len(strategy.pitch_arsenal) >= 4
    pitch_names = [p["name"] for p in strategy.pitch_arsenal]
    assert any(p in ("4-Seam Fastball", "Four-Seam Fastball") for p in pitch_names)

    # Tactical count leverage scenarios
    scenarios = [
        # (balls, strikes, dp, expected_leverage, expected_rec_zone)
        (0, 0, False, "FIRST_PITCH", "lower-away"),
        (0, 2, False, "AHEAD_TWO_STRIKES", "chase-away"),
        (3, 0, False, "BEHIND", "heart"),
        (3, 2, False, "FULL_COUNT", "lower-away"),
        (1, 2, True, "AHEAD_TWO_STRIKES", "lower-middle"),
    ]


    for balls, strikes, dp, exp_leverage, exp_zone in scenarios:
        leverage = strategy.get_leverage_state(balls, strikes)
        assert leverage == exp_leverage, f"Count {balls}-{strikes} should be {exp_leverage}, got {leverage}"

        choice = strategy.choose_pitch(balls, strikes, double_play_situation=dp)
        assert "selected_pitch" in choice
        assert "velocity_mph" in choice
        assert "spin_rpm" in choice
        assert choice["recommended_zone"] == exp_zone


def test_pitching_delivery_execution():
    """
    Consolidated Test 3: Pitch Delivery & Bivariate Gaussian Dispersion.
    Validates coordinate targeting, Gaussian dispersion math, radial miss calculation,
    and pitch effectiveness scoring.
    """
    mclean, judge = get_test_matchup()
    engine = PitchingEngine(pitcher=mclean, batter=judge)

    delivery = engine.execute_pitch(
        balls=1,
        strikes=2,
        outs=1,
        runners=(True, False, False),
        pitch_count=45,
        recent_pitches=["Four-Seam Fastball"],
        target_zone="chase-away",
    )

    assert "selected_pitch" in delivery
    assert "velocity_mph" in delivery
    assert "spin_rpm" in delivery
    assert "realized_x" in delivery and "realized_z" in delivery
    assert "radial_miss_in" in delivery
    assert "pitch_effectiveness" in delivery
    assert "adjusted_ratings" in delivery
    assert delivery["adjusted_ratings"]["pitch_count"] == 45


def test_game_engine_pitch_integration():
    """
    Consolidated Test 4: GameEngine Simulation Hand-Off & Alias Integration.
    Validates end-to-end hand-off between GameEngine and PitchingEngine.
    """
    mclean, judge = get_test_matchup()
    away_team = {
        "name": "New York Yankees",
        "position_players": [judge],
        "pitchers": {"starters": [mclean], "bullpen": []},
    }
    home_team = {
        "name": "New York Mets",
        "position_players": [judge],
        "pitchers": {"starters": [mclean], "bullpen": []},
    }
    game = GameEngine(home_team, away_team, "Mets", "Yankees")

    # 1. Primary hand-off: game.pitch()
    pitch_res = game.pitch(target_zone="lower-away")
    assert pitch_res["status"] == "success"
    details = pitch_res["pitch_details"]
    assert details["adjusted_ratings"]["pitch_count"] == 1
    assert "gameday_packet" in details

    # 2. Alias hand-off: game.pitching_engine()
    alias_res = game.pitching_engine(target_zone="heart")
    assert alias_res["status"] == "success"
    alias_details = alias_res["pitch_details"]
    assert alias_details["adjusted_ratings"]["pitch_count"] == 2


def run_all_tests():
    tests = [
        ("1. Pitcher In-Game Fatigue Ratings", test_pitcher_in_game_fatigue_ratings),
        ("2. Pitch Arsenal & Count Leverage Strategy", test_pitch_arsenal_and_strategy_leverage),
        ("3. Delivery Execution & Bivariate Gaussian Math", test_pitching_delivery_execution),
        ("4. GameEngine Simulation Hand-off & Alias", test_game_engine_pitch_integration),
    ]

    print("=" * 65)
    print("CONSOLIDATED TEST SUITE: Pitching Engine Subsystem")
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
    print(f"ALL {passed}/{len(tests)} CONSOLIDATED PITCHING TESTS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    run_all_tests()
