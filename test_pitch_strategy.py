from pathlib import Path
import sys

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database.db import get_player
from backend.engine.game_engine import GameEngine
from backend.engine.pitch_strategy import PitchStrategy


def test_pitch_strategy():
    print("=" * 60)
    print("TEST: GameEngine -> PitchStrategy Integration")
    print("=" * 60)

    # 1. Fetch domain objects
    judge = get_player(1)   # Batter (Aaron Judge)
    mclean = get_player(2)  # Pitcher (Nolan McLean)

    if not judge or not mclean:
        print("Error: Could not find players (ID 1 and ID 2) in database.")
        return

    # 2. Setup minimal teams & GameEngine
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
    # 3. Retrieve the pitcher directly from the game engine
    pitcher = game.current_pitcher_obj()
    batter = game.current_batter_obj()


    # Note: Player model stores pitch_arsenal
    arsenal = getattr(pitcher, 'pitch_arsenal', getattr(pitcher, 'arsenal', [])) # not sure what this does
    print(f"    Pitch Arsenal: {arsenal}")

    # 4. Instantiate PitchStrategy directly with this pitcher
    strategy = PitchStrategy(pitcher, batter)
    print(f"\n[2] PitchStrategy initialized:")
    print(f"    Strategy Pitcher: {strategy.pitcher.name}")
    print(f"    Strategy Arsenal attribute: {strategy.pitch_arsenal}") # ,--- WHAT'S CURRENTLY BEING TESTED - 9/5/26

    # 5. Test count scenarios through choose_pitch()
    scenarios = [
        # Currently, Mclean pitches the same way regardless of count
        ("Neutral Count", 0, 0, False),
        ("Ahead in Count", 0, 2, False),
        ("Behind in Count", 3, 0, False),
        ("Full Count", 3, 2, False),
        ("Double Play Scenario (Ahead)", 1, 2, True),
    ]

    print(f"\n[3] Testing Strategy across different counts:")
    for label, balls, strikes, dp in scenarios:
        leverage = strategy.get_leverage_state(balls, strikes)
        result = strategy.choose_pitch(balls, strikes, double_play_situation=dp)
        print(f"    • {label:<28} | Count: {balls}-{strikes} | Leverage: {leverage:<10} | Result: {result}")

    # 6. Test game.pitch() invocation (game_engine -> strategy)
    print(f"\n[4] Calling game.pitch() from GameEngine:")
    try:
        game_pitch_result = game.pitch()
        print(f"    game.pitch() returned: {game_pitch_result}")
    except Exception as e:
        print(f"    game.pitch() raised exception: {e}")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_pitch_strategy()

