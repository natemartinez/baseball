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


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Helper to deserialize raw JSON columns into standard Python objects."""
    keys = row.keys()
    pitch_arsenal_raw = row["pitch_arsenal"] if "pitch_arsenal" in keys else None

    vitals = json.loads(row["vitals"]) if "vitals" in keys and row["vitals"] else {}
    if "team" in keys and row["team"]:
        vitals["team"] = row["team"]

    number = (
        row["jersey_number"]
        if "jersey_number" in keys and row["jersey_number"] is not None
        else (row["number"] if "number" in keys else "00")
    )
    position = (
        row["roster_position"]
        if "roster_position" in keys and row["roster_position"] is not None
        else (row["position"] if "position" in keys else "DH")
    )

    data = {
        "id": row["id"],
        "name": row["name"],
        "position": str(position),
        "number": str(number),
        "vitals": vitals,
        "stats": json.loads(row["stats"]) if "stats" in keys and row["stats"] else [],
        "zones": json.loads(row["zones"]) if "zones" in keys and row["zones"] else [],
        "ratings": json.loads(row["ratings"]) if "ratings" in keys and row["ratings"] else [],
        "traits": json.loads(row["traits"]) if "traits" in keys and row["traits"] else [],
        "pitch_arsenal": json.loads(pitch_arsenal_raw) if pitch_arsenal_raw else [],
    }

    if "team" in keys and row["team"]:
        data["team"] = row["team"]
    if "role" in keys and row["role"] is not None:
        data["role"] = row["role"]
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
        cursor = conn.cursor()

        # 1. Teams lookup
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                abbreviation TEXT
            )
        """)

        # 2. Players table (stores flexible JSON blobs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                vitals TEXT NOT NULL,
                position TEXT NOT NULL,
                number TEXT NOT NULL,
                stats TEXT NOT NULL,
                zones TEXT NOT NULL,
                ratings TEXT NOT NULL,
                traits TEXT NOT NULL,
                pitch_arsenal TEXT DEFAULT '[]'
            )
        """)

        # Migration: ensure pitch_arsenal column exists if table was previously created without it
        cursor.execute("PRAGMA table_info(players);")
        existing_cols = [col[1] for col in cursor.fetchall()]
        if "pitch_arsenal" not in existing_cols:
            cursor.execute("ALTER TABLE players ADD COLUMN pitch_arsenal TEXT DEFAULT '[]';")

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


def get_or_create_team(cursor: sqlite3.Cursor, team_name: str) -> int:
    cursor.execute("SELECT id FROM teams WHERE name = ?", (team_name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO teams (name) VALUES (?)", (team_name,))
    return cursor.lastrowid


def get_all_teams() -> list[dict[str, Any]]:
    """Returns all registered teams from SQLite ordered by primary key ID."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, abbreviation FROM teams ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]


def get_team_by_id_or_name(identifier: Any) -> Optional[dict[str, Any]]:
    """Fetches a team record by ID or exact name."""
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
        cursor.execute("SELECT id, name, abbreviation FROM teams WHERE name = ? COLLATE NOCASE", (str(identifier),))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_player(
    name: str,
    vitals: dict[str, Any],
    position: str,
    number: str,
    stats: list[dict[str, Any]],
    zones: list[dict[str, Any]],
    ratings: list[dict[str, Any]],
    traits: list[dict[str, Any]],
    pitch_arsenal: Optional[list[dict[str, Any]]] = None,
    season: int = 2026,
    team_name: Optional[str] = None,
    jersey_number: Optional[str] = None,
    role: str = "starter",
    batting_order: Optional[int] = None,
    roster_status: str = "active",
    **kwargs: Any,
) -> tuple[int, bool]:
    """Inserts a new player or updates an existing record matched by name.

    Returns:
        tuple[int, bool]: (player_id, is_created)
    """
    clean_vitals = dict(vitals)
    resolved_team = team_name or clean_vitals.pop("team", None)
    clean_vitals.pop("team", None)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        # 1. Check if the player already exists
        cursor.execute("SELECT id FROM players WHERE name = ?", (name,))
        row = cursor.fetchone()

        if row:
            player_id = row[0]
            is_created = False
            cursor.execute(
                """
                UPDATE players
                SET vitals = ?, position = ?, number = ?, stats = ?, zones = ?, ratings = ?, traits = ?, pitch_arsenal = ?
                WHERE id = ?
                """,
                (
                    json.dumps(clean_vitals),
                    position,
                    str(number),
                    json.dumps(stats),
                    json.dumps(zones),
                    json.dumps(ratings),
                    json.dumps(traits),
                    json.dumps(pitch_arsenal or []),
                    player_id,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO players (name, vitals, position, number, stats, zones, ratings, traits, pitch_arsenal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    json.dumps(clean_vitals),
                    position,
                    str(number),
                    json.dumps(stats),
                    json.dumps(zones),
                    json.dumps(ratings),
                    json.dumps(traits),
                    json.dumps(pitch_arsenal or []),
                ),
            )
            player_id = cursor.lastrowid
            is_created = True

        # 2. Relate player to team in rosters table
        if resolved_team:
            team_id = get_or_create_team(cursor, resolved_team)
            resolved_jersey = str(jersey_number or number)
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
                    player_id,
                    team_id,
                    season,
                    resolved_jersey,
                    position,
                    role,
                    batting_order,
                    roster_status,
                ),
            )

        return player_id, is_created

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
                t.name AS team
            FROM players p
            JOIN rosters r ON p.id = r.player_id
            JOIN teams t ON r.team_id = t.id
            WHERE t.name = ? 
              AND r.season = ? 
              AND r.roster_status = 'active'
            ORDER BY 
              CASE WHEN r.batting_order IS NULL THEN 1 ELSE 0 END,
              r.batting_order ASC,
              p.name ASC
            """,
            (team_name, season),
        )

        return [_row_to_dict(row) for row in cursor.fetchall()]

def get_player(player_id: int, season: int = 2026) -> Optional[Player]:
    """
    Fetches a player from SQLite by primary key ID and hydrates them into
    an authoritative domain Player object.
    """
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
                t.name AS team
            FROM players p
            LEFT JOIN rosters r ON p.id = r.player_id AND r.season = ?
            LEFT JOIN teams t ON r.team_id = t.id
            WHERE p.id = ?
            """,
            (season, player_id),
        )
        row = cursor.fetchone()
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
    judge = get_player(1)
    mclean = get_player(2)

    if judge:
        print(f"Hydrated: {judge}")
        print(f"Power: {judge.get_rating('Power')} | Has Trait: {judge.has_trait('Home Run Threat')}")
    else:
        print("Player ID 1 not found.")

    if mclean:
        print(f"Hydrated: {mclean}")
        print(f"Break: {mclean.get_rating('Break')} | Has Trait: {mclean.has_trait('Spin Monster Sweeper')}")
        if mclean.pitch_arsenal:
            print(f"Arsenal: {len(mclean.pitch_arsenal)} pitches | Primary: {mclean.pitch_arsenal[0]['pitch']} ({mclean.pitch_arsenal[0]['usage_pct']}%)")
    else:
        print("Player ID 2 not found.")