from flask import Blueprint, jsonify, render_template, request

from backend.database.db import get_team_roster_players

try:
  from backend.engine.game_engine import GameEngine
except ImportError:
  from backend.game_engine import GameEngine

api_bp = Blueprint("api", __name__)

team_names = ["New York Yankees", "New York Mets"]


def load_team_roster(team_name: str) -> dict:
  """Queries SQLite via db.py and categorizes hydrated Player objects for the engine."""
  players = get_team_roster_players(team_name)

  position_players = [
      p for p in players if p.position not in ("SP", "RP", "P", "CP")
  ]
  starters = [p for p in players if p.position in ("SP", "P")]
  bullpen = [p for p in players if p.position in ("RP", "CP")]

  return {
      "team_name": team_name,
      "all_players": players,
      "position_players": position_players,
      "pitchers": {
          "starters": starters,
          "bullpen": bullpen,
      },
  }


# Initialize team rosters from database queries
team_rosters = [load_team_roster(name) for name in team_names]
game_engine = None


@api_bp.route("/")
def index():
  return render_template("index.html", teams=team_names)


@api_bp.route("/api/state")
def state():
  data = {"teams": team_names, "game": None, "lineups": [], "rotations": []}

  for i, name in enumerate(team_names):
    roster = team_rosters[i]
    lineup = [
        f"{p.number} {p.name} - {p.position}"
        for p in roster["position_players"]
    ]
    rotation = [
        f"{p.number} {p.name} - {p.position}"
        for p in roster["pitchers"]["starters"]
    ]
    data["lineups"].append({"name": name, "players": lineup})
    data["rotations"].append({"name": name, "pitchers": rotation})

  if game_engine:
    data["game"] = {
        "inning": game_engine.inning,
        "top_bottom": game_engine.top_bottom,
        "score": dict(game_engine.score),
        "outs": game_engine.outs,
        "balls": game_engine.balls,
        "strikes": game_engine.strikes,
        "bases": dict(game_engine.bases),
        "batter": (
            game_engine.current_batter().name
            if hasattr(game_engine, "current_batter")
            else None
        ),
        "pitcher": (
            game_engine.current_pitcher_obj().name
            if hasattr(game_engine, "current_pitcher_obj")
            else None
        ),
        "game_over": game_engine.game_over,
    }

  return jsonify(data)


@api_bp.route("/api/start_game", methods=["POST"])
def start_game():
  global game_engine
  away = team_rosters[0]
  home = team_rosters[1]
  game_engine = GameEngine(home, away, team_names[1], team_names[0])
  return jsonify({"status": "started"})


@api_bp.route("/api/pitch", methods=["POST"])
def pitch():
  global game_engine
  if not game_engine:
    return jsonify({"error": "Start a game first."}), 400

  result, (outs, balls, strikes) = game_engine.pitch()
  return jsonify(
      {"result": result, "outs": outs, "balls": balls, "strikes": strikes}
  )


@api_bp.route("/api/reset", methods=["POST"])
def reset():
  global game_engine, team_rosters
  # Reload fresh roster state from DB on game reset
  team_rosters = [load_team_roster(name) for name in team_names]
  away = team_rosters[0]
  home = team_rosters[1]
  game_engine = GameEngine(home, away, team_names[1], team_names[0])
  return jsonify({"status": "reset"})


@api_bp.route("/api/swap_lineup", methods=["POST"])
def swap_lineup():
  data = request.get_json()
  team_idx = int(data["team"])
  pos1 = int(data["pos1"])
  pos2 = int(data["pos2"])
  lineup = team_rosters[team_idx]["position_players"]

  if min(pos1, pos2) < 1 or max(pos1, pos2) > len(lineup):
    return jsonify({"error": "Position index out of range."}), 400

  lineup[pos1 - 1], lineup[pos2 - 1] = lineup[pos2 - 1], lineup[pos1 - 1]
  return jsonify({"status": "swapped"})


@api_bp.route("/api/swap_rotation", methods=["POST"])
def swap_rotation():
  data = request.get_json()
  team_idx = int(data["team"])
  pos1 = int(data["pos1"])
  pos2 = int(data["pos2"])
  rotation = team_rosters[team_idx]["pitchers"]["starters"]

  if min(pos1, pos2) < 1 or max(pos1, pos2) > len(rotation):
    return jsonify({"error": "Rotation index out of range."}), 400

  rotation[pos1 - 1], rotation[pos2 - 1] = (
      rotation[pos2 - 1],
      rotation[pos1 - 1],
  )
  return jsonify({"status": "swapped"})