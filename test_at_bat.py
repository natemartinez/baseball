#!/usr/bin/env python3
from pathlib import Path
import random
import sys


# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
  sys.path.insert(0, str(ROOT_DIR))

from backend.database.db import get_player

try:
  from backend.engine.game_engine import GameEngine
except ImportError:
  from backend.game_engine import GameEngine


def run_single_at_bat(seed: int = 4):
  random.seed(seed)

  # 1. Fetch hydrated domain objects directly from SQLite
  mclean = get_player(1)  # Pitcher (ID 1 - Nolan McLean)
  judge = get_player(2)   # Batter (ID 2 - Aaron Judge)

  if not judge or not mclean:
    print(
        "Error: Make sure both players are seeded in mlb.db (ID 1: McLean, ID 2:"
        " Judge)."
    )
    return


  # 2. Package into minimal roster payloads expected by GameEngine
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

  print("=" * 55)
  print(f"MATCHUP: {mclean.name} (RHP) vs. {judge.name} (RHB)")
  print("=" * 55)

  pitch_num = 0
  initial_outs = game.outs

  # 3. Step pitch-by-pitch until plate appearance concludes
  while True:
    pitch_num += 1
    res = game.pitch()
    details = res['pitch_details']
    result = details['description']
    balls, strikes, outs = game.balls, game.strikes, game.outs

    print(f"Pitch {pitch_num:>2}: {result:<28} | Count: {balls}-{strikes}")

    # A plate appearance ends when outs increase or the count resets to 0-0 after pitch 1
    at_bat_over = (
        outs > initial_outs
        or (balls == 0 and strikes == 0 and pitch_num > 1)
        or any(
            term in result.lower()
            for term in [
                "strikeout",
                "walk",
                "single",
                "double",
                "triple",
                "home run",
                "groundout",
                "flyout",
                "pop out",
                "line out",
            ]
        )
    )

    if at_bat_over:
      print("-" * 55)
      print(f"Final Outcome: {result.strip()}")
      print(f"Total Pitches: {pitch_num}")
      print("=" * 55)
      break


if __name__ == "__main__":
  run_single_at_bat(seed=4)