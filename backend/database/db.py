import json
from pathlib import Path
import sqlite3
import sys
from typing import Any, Optional

# Ensure repository root is on sys.path when script is executed directly
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.models import Player

# Resolves to backend/database/mlb.db regardless of execution directory
DB_DIR = Path(__file__).resolve().parent
DB_PATH = DB_DIR / "mlb.db"


LEGACY_PLAYER_ID_MAP: dict[int, int] = {
    1: 101,  # Nolan McLean (P)
    2: 201,  # Aaron Judge (RF)
    3: 202,  # Juan Soto (RF)
    4: 199,  # Gleyber Torres (2B)
    5: 203,  # Giancarlo Stanton (DH)
    6: 301,  # Francisco Lindor (SS)
    7: 302,  # Pete Alonso (1B)
    8: 401,  # Gerrit Cole (P)
    9: 102,  # Kodai Senga (P)
}


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Helper to deserialize raw JSON columns into standard Python objects.
    
    Guarantees exact parity with seed_data.json for pitchers while
    providing backward compatibility aliases.
    """
    keys = row.keys()

    # Raw column deserialization
    raw_ratings = json.loads(row["ratings"]) if "ratings" in keys and row["ratings"] else {}
    raw_arsenal = json.loads(row["arsenal"]) if "arsenal" in keys and row["arsenal"] else (
        json.loads(row["pitch_arsenal"]) if "pitch_arsenal" in keys and row["pitch_arsenal"] else []
    )
    raw_motion_bio = json.loads(row["motion_bio"]) if "motion_bio" in keys and row["motion_bio"] else {}
    raw_season_stats = json.loads(row["season_stats"]) if "season_stats" in keys and row["season_stats"] else {}
    raw_live_game_stats = json.loads(row["live_game_stats"]) if "live_game_stats" in keys and row["live_game_stats"] else {}
    raw_hot_zones = json.loads(row["hot_zones"]) if "hot_zones" in keys and row["hot_zones"] else []
    raw_zones = json.loads(row["zones"]) if "zones" in keys and row["zones"] else []
    raw_traits = json.loads(row["traits"]) if "traits" in keys and row["traits"] else []
    raw_vitals = json.loads(row["vitals"]) if "vitals" in keys and row["vitals"] else {}

    position = (
        row["roster_position"]
        if "roster_position" in keys and row["roster_position"] is not None
        else (row["position"] if "position" in keys else "DH")
    )

    jersey_val = (
        row["jersey_number"]
        if "jersey_number" in keys and row["jersey_number"] is not None
        else (row["number"] if "number" in keys else 0)
    )
    jersey_num_int = int(jersey_val) if str(jersey_val).isdigit() else 0

    is_pitcher = position in ("P", "SP", "RP", "CP") or len(raw_arsenal) > 0

    # Team abbreviation vs team full name
    team_abbr = row["team_abbr"] if "team_abbr" in keys and row["team_abbr"] else None
    team_name = row["team"] if "team" in keys and row["team"] else None
    if not team_abbr and "team" in keys and row["team"]:
        abbr_map = {"New York Mets": "NYM", "New York Yankees": "NYY"}
        team_abbr = abbr_map.get(row["team"], row["team"])
    if not team_abbr:
        team_abbr = "NYM" if is_pitcher else "NYY"

    role_val = row["role"] if "role" in keys and row["role"] is not None else ("pitcher" if is_pitcher else "starter")
    throws_val = row["throws"] if "throws" in keys and row["throws"] else raw_vitals.get("throws", "R")
    bats_val = row["bats"] if "bats" in keys and row["bats"] else raw_vitals.get("bats", "R")

    if not raw_motion_bio and raw_vitals.get("motion_bio"):
        raw_motion_bio = raw_vitals["motion_bio"]

    if is_pitcher:
        # EXACT PITCHER JSON SCHEMA matching seed_data.json
        data = {
            "id": row["id"],
            "name": row["name"],
            "team": team_abbr or "NYM",
            "position": str(position),
            "role": str(role_val),
            "jersey_number": jersey_num_int,
            "throws": str(throws_val),
            "bats": str(bats_val),
            "motion_bio": raw_motion_bio,
            "ratings": raw_ratings,
            "arsenal": raw_arsenal,
            "season_stats": raw_season_stats,
            "live_game_stats": raw_live_game_stats,
        }
    else:
        # Batter schema matching seed_data.json
        data = {
            "id": row["id"],
            "name": row["name"],
            "team": team_abbr or "NYY",
            "position": str(position),
            "role": str(role_val),
            "jersey_number": jersey_num_int,
            "throws": str(throws_val),
            "bats": str(bats_val),
            "ratings": raw_ratings,
            "traits": raw_traits,
            "hot_zones": raw_hot_zones or raw_zones,
            "season_stats": raw_season_stats,
            "live_game_stats": raw_live_game_stats,
        }

    # Backward compatibility aliases
    data["number"] = str(jersey_num_int)
    data["pitch_arsenal"] = raw_arsenal
    vitals_dict = dict(raw_vitals)
    vitals_dict["team"] = team_name or team_abbr
    vitals_dict["throws"] = str(throws_val)
    vitals_dict["bats"] = str(bats_val)
    if raw_motion_bio:
        vitals_dict["motion_bio"] = raw_motion_bio
        for mb_k, mb_v in raw_motion_bio.items():
            vitals_dict[mb_k] = mb_v
    data["vitals"] = vitals_dict

    # stats alias (list format for older consumers)
    if "stats" in keys and row["stats"] and row["stats"] != "[]":
        try:
            data["stats"] = json.loads(row["stats"])
        except Exception:
            data["stats"] = [raw_season_stats] if raw_season_stats else []
    else:
        data["stats"] = [raw_season_stats] if raw_season_stats else []

    data["zones"] = raw_zones or raw_hot_zones
    if "traits" not in data:
        data["traits"] = raw_traits

    if "roster_status" in keys and row["roster_status"] is not None:
        data["roster_status"] = row["roster_status"]
    if "batting_order" in keys and row["batting_order"] is not None:
        data["batting_order"] = row["batting_order"]
    if "season" in keys and row["season"] is not None:
        data["season"] = row["season"]

    return data


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        cursor = conn.cursor()

        # 1. Teams lookup
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                abbreviation TEXT
            )
        """)

        # Migration: ensure abbreviation column exists on teams
        cursor.execute("PRAGMA table_info(teams);")
        team_cols = [col[1] for col in cursor.fetchall()]
        if "abbreviation" not in team_cols:
            cursor.execute("ALTER TABLE teams ADD COLUMN abbreviation TEXT;")

        # 2. Players table (stores exact player attributes + flexible JSON blobs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                vitals TEXT DEFAULT '{}',
                position TEXT NOT NULL,
                number TEXT DEFAULT '00',
                jersey_number INTEGER,
                team TEXT,
                role TEXT,
                throws TEXT,
                bats TEXT,
                stats TEXT DEFAULT '[]',
                zones TEXT DEFAULT '[]',
                hot_zones TEXT DEFAULT '[]',
                ratings TEXT NOT NULL,
                traits TEXT DEFAULT '[]',
                pitch_arsenal TEXT DEFAULT '[]',
                arsenal TEXT DEFAULT '[]',
                motion_bio TEXT DEFAULT '{}',
                season_stats TEXT DEFAULT '{}',
                live_game_stats TEXT DEFAULT '{}'
            )
        """)

        # Migration: dynamically add any missing columns to existing players table
        cursor.execute("PRAGMA table_info(players);")
        existing_cols = [col[1] for col in cursor.fetchall()]
        player_col_defs = [
            ("jersey_number", "INTEGER"),
            ("team", "TEXT"),
            ("role", "TEXT"),
            ("throws", "TEXT"),
            ("bats", "TEXT"),
            ("hot_zones", "TEXT DEFAULT '[]'"),
            ("pitch_arsenal", "TEXT DEFAULT '[]'"),
            ("arsenal", "TEXT DEFAULT '[]'"),
            ("motion_bio", "TEXT DEFAULT '{}'"),
            ("season_stats", "TEXT DEFAULT '{}'"),
            ("live_game_stats", "TEXT DEFAULT '{}'"),
        ]
        for col_name, col_type in player_col_defs:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE players ADD COLUMN {col_name} {col_type};")

        # 3. Junction table (depends on 1 & 2 above)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rosters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                season INTEGER NOT NULL,
                jersey_number TEXT,
                position TEXT,
                role TEXT DEFAULT 'starter',
                batting_order INTEGER,
                roster_status TEXT DEFAULT 'active',
                FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                UNIQUE(player_id, season)
            )
        """)

        # Migration: add new roster columns if table existed under older schema
        cursor.execute("PRAGMA table_info(rosters);")
        roster_cols = [col[1] for col in cursor.fetchall()]
        for col_name, col_type in [
            ("jersey_number", "TEXT"),
            ("position", "TEXT"),
            ("role", "TEXT DEFAULT 'starter'"),
            ("batting_order", "INTEGER"),
        ]:
            if col_name not in roster_cols:
                cursor.execute(f"ALTER TABLE rosters ADD COLUMN {col_name} {col_type};")

        # Indexes for fast B-tree seeks
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rosters_team_season 
            ON rosters(team_id, season, roster_status);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rosters_player 
            ON rosters(player_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_players_name 
            ON players(name);
        """)


def get_or_create_team(
    cursor: sqlite3.Cursor, team_name: str, abbreviation: Optional[str] = None
) -> int:
    cursor.execute("SELECT id, abbreviation FROM teams WHERE name = ?", (team_name,))
    row = cursor.fetchone()
    if row:
        if abbreviation and not row[1]:
            cursor.execute("UPDATE teams SET abbreviation = ? WHERE id = ?", (abbreviation, row[0]))
        return row[0]
    cursor.execute("INSERT INTO teams (name, abbreviation) VALUES (?, ?)", (team_name, abbreviation))
    return cursor.lastrowid


def get_all_teams() -> list[dict[str, Any]]:
    """Returns all registered teams from SQLite ordered by primary key ID."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, abbreviation FROM teams ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]


def get_team_by_id_or_name(identifier: Any) -> Optional[dict[str, Any]]:
    """Fetches a team record by ID, exact name, or abbreviation."""
    if identifier is None:
        return None
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if str(identifier).isdigit():
            cursor.execute("SELECT id, name, abbreviation FROM teams WHERE id = ?", (int(identifier),))
            row = cursor.fetchone()
            if row:
                return dict(row)
        cursor.execute(
            "SELECT id, name, abbreviation FROM teams WHERE name = ? COLLATE NOCASE OR abbreviation = ? COLLATE NOCASE",
            (str(identifier), str(identifier)),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def add_player(
    name: str,
    position: str = "DH",
    number: Optional[str] = None,
    ratings: Optional[Any] = None,
    vitals: Optional[dict[str, Any]] = None,
    stats: Optional[Any] = None,
    zones: Optional[list[dict[str, Any]]] = None,
    traits: Optional[list[Any]] = None,
    pitch_arsenal: Optional[list[dict[str, Any]]] = None,
    season: int = 2026,
    team_name: Optional[str] = None,
    jersey_number: Optional[Any] = None,
    role: Optional[str] = None,
    batting_order: Optional[int] = None,
    roster_status: str = "active",
    player_id: Optional[int] = None,
    team: Optional[str] = None,
    throws: Optional[str] = None,
    bats: Optional[str] = None,
    motion_bio: Optional[dict[str, Any]] = None,
    arsenal: Optional[list[dict[str, Any]]] = None,
    season_stats: Optional[dict[str, Any]] = None,
    live_game_stats: Optional[dict[str, Any]] = None,
    hot_zones: Optional[list[dict[str, Any]]] = None,
    id: Optional[int] = None,
    **kwargs: Any,
) -> tuple[int, bool]:
    """Inserts a new player or updates an existing record matched by ID or name.

    Returns:
        tuple[int, bool]: (player_id, is_created)
    """
    clean_vitals = dict(vitals or {})
    resolved_team = team or team_name or clean_vitals.pop("team", None)
    clean_vitals.pop("team", None)

    explicit_id = id if id is not None else player_id
    resolved_jersey_num = (
        int(jersey_number)
        if jersey_number is not None and str(jersey_number).isdigit()
        else (int(number) if number and str(number).isdigit() else 99)
    )
    resolved_jersey_str = str(jersey_number or number or resolved_jersey_num)
    resolved_arsenal = arsenal if arsenal is not None else (pitch_arsenal or [])
    is_pitcher = position in ("P", "SP", "RP", "CP") or len(resolved_arsenal) > 0

    resolved_role = role or ("pitcher" if is_pitcher else "starter")
    resolved_throws = str(throws or clean_vitals.get("throws") or "R")
    resolved_bats = str(bats or clean_vitals.get("bats") or "R")
    resolved_motion_bio = motion_bio or clean_vitals.get("motion_bio") or {}
    resolved_season_stats = (
        season_stats
        if season_stats is not None
        else (stats if isinstance(stats, dict) else (stats[0] if isinstance(stats, list) and stats else {}))
    )
    resolved_live_game_stats = live_game_stats or {}
    resolved_hot_zones = hot_zones or zones or []
    resolved_ratings = ratings or {}
    resolved_traits = traits or []

    # Map team abbreviation and full name
    abbr_to_full = {"NYM": "New York Mets", "NYY": "New York Yankees"}
    full_to_abbr = {"New York Mets": "NYM", "New York Yankees": "NYY"}
    team_full = abbr_to_full.get(resolved_team, resolved_team) if resolved_team else None
    team_abbr = full_to_abbr.get(resolved_team, resolved_team) if resolved_team else None

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        # 1. Check if the player already exists (by ID or by name)
        row = None
        if explicit_id is not None:
            cursor.execute("SELECT id FROM players WHERE id = ?", (explicit_id,))
            row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT id FROM players WHERE name = ?", (name,))
            row = cursor.fetchone()

        if row:
            pid = row[0]
            is_created = False
            cursor.execute(
                """
                UPDATE players
                SET name = ?, vitals = ?, position = ?, number = ?, jersey_number = ?, team = ?, role = ?,
                    throws = ?, bats = ?, stats = ?, zones = ?, hot_zones = ?, ratings = ?, traits = ?,
                    pitch_arsenal = ?, arsenal = ?, motion_bio = ?, season_stats = ?, live_game_stats = ?
                WHERE id = ?
                """,
                (
                    name,
                    json.dumps(clean_vitals),
                    position,
                    resolved_jersey_str,
                    resolved_jersey_num,
                    team_abbr or team_full,
                    resolved_role,
                    resolved_throws,
                    resolved_bats,
                    json.dumps(stats if isinstance(stats, list) else [resolved_season_stats]),
                    json.dumps(zones or resolved_hot_zones),
                    json.dumps(resolved_hot_zones),
                    json.dumps(resolved_ratings),
                    json.dumps(resolved_traits),
                    json.dumps(resolved_arsenal),
                    json.dumps(resolved_arsenal),
                    json.dumps(resolved_motion_bio),
                    json.dumps(resolved_season_stats),
                    json.dumps(resolved_live_game_stats),
                    pid,
                ),
            )
        else:
            if explicit_id is not None:
                cursor.execute(
                    """
                    INSERT INTO players (
                        id, name, vitals, position, number, jersey_number, team, role, throws, bats,
                        stats, zones, hot_zones, ratings, traits, pitch_arsenal, arsenal, motion_bio,
                        season_stats, live_game_stats
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        explicit_id,
                        name,
                        json.dumps(clean_vitals),
                        position,
                        resolved_jersey_str,
                        resolved_jersey_num,
                        team_abbr or team_full,
                        resolved_role,
                        resolved_throws,
                        resolved_bats,
                        json.dumps(stats if isinstance(stats, list) else [resolved_season_stats]),
                        json.dumps(zones or resolved_hot_zones),
                        json.dumps(resolved_hot_zones),
                        json.dumps(resolved_ratings),
                        json.dumps(resolved_traits),
                        json.dumps(resolved_arsenal),
                        json.dumps(resolved_arsenal),
                        json.dumps(resolved_motion_bio),
                        json.dumps(resolved_season_stats),
                        json.dumps(resolved_live_game_stats),
                    ),
                )
                pid = explicit_id
            else:
                cursor.execute(
                    """
                    INSERT INTO players (
                        name, vitals, position, number, jersey_number, team, role, throws, bats,
                        stats, zones, hot_zones, ratings, traits, pitch_arsenal, arsenal, motion_bio,
                        season_stats, live_game_stats
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        json.dumps(clean_vitals),
                        position,
                        resolved_jersey_str,
                        resolved_jersey_num,
                        team_abbr or team_full,
                        resolved_role,
                        resolved_throws,
                        resolved_bats,
                        json.dumps(stats if isinstance(stats, list) else [resolved_season_stats]),
                        json.dumps(zones or resolved_hot_zones),
                        json.dumps(resolved_hot_zones),
                        json.dumps(resolved_ratings),
                        json.dumps(resolved_traits),
                        json.dumps(resolved_arsenal),
                        json.dumps(resolved_arsenal),
                        json.dumps(resolved_motion_bio),
                        json.dumps(resolved_season_stats),
                        json.dumps(resolved_live_game_stats),
                    ),
                )
                pid = cursor.lastrowid
            is_created = True

        # 2. Relate player to team in rosters table
        if team_full:
            team_id = get_or_create_team(cursor, team_full, abbreviation=team_abbr)
            cursor.execute(
                """
                INSERT INTO rosters (
                    player_id, team_id, season, jersey_number, position, role, batting_order, roster_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(player_id, season) DO UPDATE SET
                    team_id = excluded.team_id,
                    jersey_number = excluded.jersey_number,
                    position = excluded.position,
                    role = excluded.role,
                    batting_order = excluded.batting_order,
                    roster_status = excluded.roster_status
                """,
                (
                    pid,
                    team_id,
                    season,
                    resolved_jersey_str,
                    position,
                    resolved_role,
                    batting_order,
                    roster_status,
                ),
            )

        return pid, is_created


def get_team_roster(
    team_name: str, season: int = 2026
) -> list[dict[str, Any]]:
    """Instant B-tree lookup for all active players on a team."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 
                p.*,
                r.jersey_number,
                r.position AS roster_position,
                r.role,
                r.batting_order,
                r.roster_status,
                r.season,
                t.name AS team,
                t.abbreviation AS team_abbr
            FROM players p
            JOIN rosters r ON p.id = r.player_id
            JOIN teams t ON r.team_id = t.id
            WHERE (t.name = ? COLLATE NOCASE OR t.abbreviation = ? COLLATE NOCASE)
              AND r.season = ? 
              AND r.roster_status = 'active'
            ORDER BY 
              CASE WHEN r.batting_order IS NULL THEN 1 ELSE 0 END,
              r.batting_order ASC,
              p.id ASC
            """,
            (team_name, team_name, season),
        )

        return [_row_to_dict(row) for row in cursor.fetchall()]


def _fetch_player_row(cursor: sqlite3.Cursor, target_id: int, season: int) -> Optional[sqlite3.Row]:
    cursor.execute(
        """
        SELECT 
            p.*,
            r.jersey_number,
            r.position AS roster_position,
            r.role,
            r.batting_order,
            r.roster_status,
            r.season,
            t.name AS team,
            t.abbreviation AS team_abbr
        FROM players p
        LEFT JOIN rosters r ON p.id = r.player_id AND r.season = ?
        LEFT JOIN teams t ON r.team_id = t.id
        WHERE p.id = ?
        """,
        (season, target_id),
    )
    return cursor.fetchone()


def get_player(player_id: int, season: int = 2026) -> Optional[Player]:
    """
    Fetches a player from SQLite by primary key ID and hydrates them into
    an authoritative domain Player object.
    Supports authoritative IDs (101, 401, 102) with legacy alias fallback (1..9).
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        row = _fetch_player_row(cursor, player_id, season)
        if not row and player_id in LEGACY_PLAYER_ID_MAP:
            mapped_id = LEGACY_PLAYER_ID_MAP[player_id]
            row = _fetch_player_row(cursor, mapped_id, season)

        if not row:
            return None

        raw_data = _row_to_dict(row)
        return Player.from_dict(raw_data)

def get_team_roster_players(
    team_name: str, season: int = 2026
) -> list[Player]:
    """
    Primary Domain Loader: Fetches active roster players for a given team
    and hydrates them into domain Player objects.
    """
    raw_players = get_team_roster(team_name, season)
    return [Player.from_dict(p) for p in raw_players]


if __name__ == "__main__":
    # Smoke test: inspect DB output and object hydration
    mclean = get_player(101)
    judge = get_player(201)

    if mclean:
        print(f"Hydrated: {mclean}")
        print(f"Break: {mclean.get_rating('Break')} | Velocity: {mclean.get_rating('Velocity')}")
        if mclean.pitch_arsenal:
            print(f"Arsenal: {len(mclean.pitch_arsenal)} pitches | Primary: {mclean.pitch_arsenal[0].get('name')} ({mclean.pitch_arsenal[0].get('velocity_mph')} mph)")
    else:
        print("Player ID 101 not found.")

    if judge:
        print(f"Hydrated: {judge}")
        print(f"Power: {judge.get_rating('Power')} | Contact: {judge.get_rating('Contact')}")
    else:
        print("Player ID 201 not found.")