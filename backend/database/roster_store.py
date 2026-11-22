"""
In-Memory Roster Store.

Provides thread-safe, pre-warmed caching of teams, rosters, and Player domain objects.
Eliminates database queries and deserialization overhead during active game execution,
delivering O(1) constant-time access for runtime operations.
"""

import copy
import json
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Tuple

from backend.database.db import (
    LEGACY_PLAYER_ID_MAP,
    get_all_teams as db_get_all_teams,
    get_team_roster_players as db_get_team_roster_players,
)
from backend.engine.models.player import (
    DEFAULT_DEFENSIVE_RATINGS,
    Player,
)


class RosterStore:
    """Thread-safe in-memory cache for teams, rosters, and players."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._teams: List[Dict[str, Any]] = []
        self._teams_by_id: Dict[int, Dict[str, Any]] = {}
        self._teams_by_name: Dict[str, Dict[str, Any]] = {}
        self._rosters: Dict[Tuple[int, int], Dict[str, Any]] = {}
        self._players_by_id: Dict[Tuple[int, int], Player] = {}
        self._is_warmed: bool = False

    @property
    def is_warmed(self) -> bool:
        with self._lock:
            return self._is_warmed

    def clear(self) -> None:
        """Clears all cached in-memory structures."""
        with self._lock:
            self._teams.clear()
            self._teams_by_id.clear()
            self._teams_by_name.clear()
            self._rosters.clear()
            self._players_by_id.clear()
            self._is_warmed = False

    def warmup(self, season: int = 2026, force: bool = False) -> None:
        """
        Eagerly loads all teams and rosters into memory from SQLite and latest_rosters.json.
        Guarantees that subsequent queries execute in O(1) with zero SQL.
        """
        with self._lock:
            if self._is_warmed and not force:
                return

            raw_teams = db_get_all_teams()
            self._teams = [dict(t) for t in raw_teams]

            # Attempt to load supplementary 40-man roster data
            latest_roster_data = {}
            latest_file = Path(__file__).resolve().parent / "latest_rosters.json"
            if latest_file.exists():
                try:
                    with open(latest_file, "r", encoding="utf-8") as f:
                        latest_roster_data = json.load(f)
                except Exception:
                    latest_roster_data = {}

            for t in self._teams:
                t_id = t["id"]
                t_name = t["name"]
                t_abbr = t.get("abbreviation") or ("NYY" if "yankees" in t_name.lower() else "NYM")

                self._teams_by_id[t_id] = t
                self._teams_by_name[t_name.lower()] = t
                if t_abbr:
                    self._teams_by_name[t_abbr.lower()] = t

                db_players = list(db_get_team_roster_players(t_name, season=season))
                existing_names = {p.name.lower(): p for p in db_players}
                all_team_players = list(db_players)

                # Supplement with 40-man roster from latest_rosters.json if available
                team_json = latest_roster_data.get("teams", {}).get(t_abbr.upper(), {})
                raw_players = team_json.get("all_players", [])

                for idx, raw in enumerate(raw_players):
                    p_name = raw.get("name", "").strip()
                    if not p_name or p_name.lower() in existing_names:
                        continue

                    is_pitcher = raw.get("is_pitcher", False)
                    jersey_str = str(raw.get("jersey_number", "00"))
                    jersey_num = int(jersey_str) if jersey_str.isdigit() else (idx + 10)
                    mlb_id = raw.get("mlb_id") or (3000 + (t_id * 100) + idx)

                    if is_pitcher:
                        gs = raw.get("season_stats", {}).get("gamesStarted", 0)
                        role = "starter" if gs > 5 else "bullpen"
                        pos = "SP" if role == "starter" else "RP"

                        arsenal = [
                            {
                                "id": "4SFB",
                                "name": "Four-Seam Fastball",
                                "category": "FASTBALL",
                                "velocity_mph": 95.0,
                                "velocity_min_mph": 93.0,
                                "velocity_max_mph": 97.0,
                                "velocity_display": "93–97 mph",
                                "command": 82.0,
                                "control_rating": 82.0,
                                "max_radius_inches": 3.0,
                                "sigma": 0.10,
                                "spin_rate_rpm": 2400,
                                "spin_axis_deg": 215.0,
                                "horizontal_break_in": -7.0,
                                "induced_vertical_break_in": 15.0,
                                "tunnel_partners": ["SL", "CH"],
                                "spin_rpm": 2400,
                            },
                            {
                                "id": "SL",
                                "name": "Slider",
                                "category": "BREAKING",
                                "velocity_mph": 85.0,
                                "velocity_min_mph": 83.0,
                                "velocity_max_mph": 87.0,
                                "velocity_display": "83–87 mph",
                                "command": 80.0,
                                "control_rating": 80.0,
                                "max_radius_inches": 3.2,
                                "sigma": 0.107,
                                "spin_rate_rpm": 2600,
                                "spin_axis_deg": 90.0,
                                "horizontal_break_in": 6.5,
                                "induced_vertical_break_in": 2.0,
                                "tunnel_partners": ["4SFB", "CH"],
                                "spin_rpm": 2600,
                            },
                            {
                                "id": "CH",
                                "name": "Changeup",
                                "category": "OFFSPEED",
                                "velocity_mph": 87.0,
                                "velocity_min_mph": 85.0,
                                "velocity_max_mph": 89.0,
                                "velocity_display": "85–89 mph",
                                "command": 78.0,
                                "control_rating": 78.0,
                                "max_radius_inches": 3.4,
                                "sigma": 0.113,
                                "spin_rate_rpm": 1800,
                                "spin_axis_deg": 240.0,
                                "horizontal_break_in": -12.0,
                                "induced_vertical_break_in": 7.0,
                                "tunnel_partners": ["4SFB", "SL"],
                                "spin_rpm": 1800,
                            },
                        ]
                        ratings = {
                            "velocity_rating": 94.0,
                            "break_rating": 82.0,
                            "control": 82.0,
                            "stamina": 85.0 if role == "starter" else 65.0,
                            "composure": 80.0,
                            "consistency": 82.0,
                        }
                        p_obj = Player.from_dict({
                            "id": mlb_id,
                            "name": p_name,
                            "number": str(jersey_num),
                            "jersey_number": jersey_num,
                            "position": pos,
                            "team": t_abbr,
                            "is_pitcher": True,
                            "role": role,
                            "batting_order": None,
                            "roster_status": "active",
                            "season": season,
                            "stamina": 85.0 if role == "starter" else 65.0,
                            "composure": 80.0,
                            "consistency": 82.0,
                            "ratings": ratings,
                            "arsenal": arsenal,
                            "pitch_arsenal": arsenal,
                            "motion_bio": {
                                "arm_slot": "THREE_QUARTERS",
                                "arm_slot_angle_deg": 45.0,
                                "release_point_ft": {"x": -1.8, "y": 54.5, "z": 5.9},
                            },
                            "season_stats": raw.get("season_stats", {}),
                            "live_game_stats": {"pitch_count": 0, "strikes": 0, "balls": 0, "innings_pitched": 0.0, "hits": 0, "earned_runs": 0, "walks": 0, "strikeouts": 0},
                        })
                    else:
                        pos = raw.get("position", "DH")
                        try:
                            avg = float(raw.get("season_stats", {}).get("avg", ".250") or ".250")
                        except (ValueError, TypeError):
                            avg = 0.250
                        try:
                            slg = float(raw.get("season_stats", {}).get("slg", ".400") or ".400")
                        except (ValueError, TypeError):
                            slg = 0.400
                        contact = min(99.0, max(60.0, avg * 300.0))
                        power = min(99.0, max(50.0, slg * 180.0))
                        ratings = {
                            **DEFAULT_DEFENSIVE_RATINGS,
                            "contact": round(contact, 1),
                            "power": round(power, 1),
                            "speed": 75.0,
                            "fielding": 75.0,
                            "vision": 75.0,
                        }
                        p_obj = Player.from_dict({
                            "id": mlb_id,
                            "name": p_name,
                            "number": str(jersey_num),
                            "jersey_number": jersey_num,
                            "position": pos,
                            "team": t_abbr,
                            "is_pitcher": False,
                            "role": "batter",
                            "batting_order": 999,
                            "roster_status": "active",
                            "season": season,
                            "ratings": ratings,
                            "zones": {},
                            "traits": [],
                            "season_stats": raw.get("season_stats", {}),
                        })

                    all_team_players.append(p_obj)
                    existing_names[p_name.lower()] = p_obj

                pos_players = [p for p in all_team_players if not p.is_pitcher]
                pitchers = [p for p in all_team_players if p.is_pitcher]

                seen_pitcher_ids = set()
                unique_pitchers = []
                for p in pitchers:
                    if p.id not in seen_pitcher_ids:
                        seen_pitcher_ids.add(p.id)
                        unique_pitchers.append(p)

                db_pitchers = [p for p in db_players if p.is_pitcher]
                primary_sp = db_pitchers[0] if db_pitchers else None

                explicit_starters = [
                    p for p in unique_pitchers
                    if getattr(p, "role", None) == "starter" or getattr(p, "position", None) == "SP"
                ]
                if primary_sp and primary_sp not in explicit_starters:
                    explicit_starters.insert(0, primary_sp)
                elif primary_sp and primary_sp in explicit_starters:
                    explicit_starters.remove(primary_sp)
                    explicit_starters.insert(0, primary_sp)

                starters = explicit_starters[:5]
                starter_ids = {p.id for p in starters}
                bullpen = [p for p in unique_pitchers if p.id not in starter_ids]

                # Position players: sort and assign sequential batting order
                ordered_pos = sorted(
                    [p for p in pos_players if getattr(p, "batting_order", None) is not None and getattr(p, "batting_order", 999) < 999],
                    key=lambda p: getattr(p, "batting_order", 999),
                )
                unordered_pos = [p for p in pos_players if p not in ordered_pos]
                current_order = len(ordered_pos) + 1
                for p in unordered_pos:
                    p.batting_order = current_order
                    current_order += 1
                    ordered_pos.append(p)

                position_players = ordered_pos

                self._rosters[(t_id, season)] = {
                    "team_id": t_id,
                    "team_name": t_name,
                    "all_players": list(all_team_players),
                    "position_players": position_players,
                    "pitchers": {
                        "starters": starters,
                        "bullpen": bullpen,
                    },
                }

                for p in all_team_players:
                    if p.id is not None:
                        self._players_by_id[(int(p.id), season)] = p

            self._is_warmed = True

    def get_all_teams(self) -> List[Dict[str, Any]]:
        """Returns all registered teams in O(1) time."""
        if not self._is_warmed:
            self.warmup()
        with self._lock:
            return [dict(t) for t in self._teams]

    def get_team(self, identifier: Any) -> Optional[Dict[str, Any]]:
        """Resolves team by integer ID, string ID, exact name, or abbreviation in O(1) time."""
        if identifier is None:
            return None
        if not self._is_warmed:
            self.warmup()

        with self._lock:
            # Check by integer ID
            if isinstance(identifier, int) or str(identifier).isdigit():
                t = self._teams_by_id.get(int(identifier))
                if t:
                    return dict(t)

            # Check by name or abbreviation (case-insensitive)
            key = str(identifier).strip().lower()
            t = self._teams_by_name.get(key)
            if t:
                return dict(t)

            return None

    def get_roster(
        self, team_identifier: Any, season: int = 2026, clone: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves categorized roster for a team in O(1) time.
        When clone=True, returns deep copies of Player instances to isolate in-game mutations.
        """
        if not self._is_warmed:
            self.warmup(season=season)

        team = self.get_team(team_identifier)
        if not team:
            return None

        team_id = team["id"]
        with self._lock:
            cached = self._rosters.get((team_id, season))
            if not cached:
                return None

            if clone:
                return {
                    "team_id": cached["team_id"],
                    "team_name": cached["team_name"],
                    "all_players": [copy.deepcopy(p) for p in cached.get("all_players", [])],
                    "position_players": [copy.deepcopy(p) for p in cached["position_players"]],
                    "pitchers": {
                        "starters": [copy.deepcopy(p) for p in cached["pitchers"]["starters"]],
                        "bullpen": [copy.deepcopy(p) for p in cached["pitchers"]["bullpen"]],
                    },
                }

            return {
                "team_id": cached["team_id"],
                "team_name": cached["team_name"],
                "all_players": list(cached.get("all_players", [])),
                "position_players": list(cached["position_players"]),
                "pitchers": {
                    "starters": list(cached["pitchers"]["starters"]),
                    "bullpen": list(cached["pitchers"]["bullpen"]),
                },
            }

    def get_player(
        self, player_id: Any, season: int = 2026, clone: bool = False
    ) -> Optional[Player]:
        """Resolves player by authoritative primary key ID or legacy alias in O(1) time."""
        if player_id is None:
            return None
        if not self._is_warmed:
            self.warmup(season=season)

        try:
            pid = int(player_id)
        except (ValueError, TypeError):
            return None

        with self._lock:
            p = self._players_by_id.get((pid, season))
            if not p and pid in LEGACY_PLAYER_ID_MAP:
                mapped_id = LEGACY_PLAYER_ID_MAP[pid]
                p = self._players_by_id.get((mapped_id, season))

            if p and clone:
                return copy.deepcopy(p)
            return p


# Global singleton instance
roster_store = RosterStore()
