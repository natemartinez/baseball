"""
Thin client for the Yahoo Fantasy Sports API.

Usage:
  from yahoo_api import YahooFantasyAPI
  api = YahooFantasyAPI()
  print(api.get_user_games())
"""

import requests
from yahoo_auth import get_access_token

_BASE = "https://fantasysports.yahooapis.com/fantasy/v2"


class YahooFantasyAPI:
    def _get(self, path: str, params: dict = None) -> dict:
        token = get_access_token()
        resp = requests.get(
            f"{_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params={"format": "json", **(params or {})},
        )
        resp.raise_for_status()
        return resp.json()

    def get_user_games(self) -> dict:
        """All fantasy games the logged-in user is in."""
        return self._get("/users;use_login=1/games")

    def get_user_teams(self, game_key: str = "mlb") -> dict:
        """All teams for a user in a given game (default: mlb)."""
        return self._get(f"/users;use_login=1/games;game_keys={game_key}/teams")

    def get_league(self, league_key: str) -> dict:
        """Metadata about a specific league."""
        return self._get(f"/league/{league_key}")

    def get_league_standings(self, league_key: str) -> dict:
        """Standings for a league."""
        return self._get(f"/league/{league_key}/standings")

    def get_team_roster(self, team_key: str) -> dict:
        """Current roster for a team."""
        return self._get(f"/team/{team_key}/roster/players")

    def get_player_stats(self, player_key: str, season: int = 2025) -> dict:
        """Season stats for a player."""
        return self._get(
            f"/player/{player_key}/stats",
            params={"type": "season", "season": season},
        )

    def search_players(self, game_key: str, search: str) -> dict:
        """Search for players by name in a game."""
        return self._get(
            f"/game/{game_key}/players",
            params={"search": search},
        )
