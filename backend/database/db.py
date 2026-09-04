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
    return {
        "id": row["id"],
        "name": row["name"],
        "position": row["position"],
        "number": row["number"],
        "vitals": json.loads(row["vitals"]),
        "stats": json.loads(row["stats"]),
        "zones": json.loads(row["zones"]),
        "ratings": json.loads(row["ratings"]),
        "traits": json.loads(row["traits"]),
    }


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
                traits TEXT NOT NULL
            )
        """)

        # 3. Junction table (depends on 1 & 2 above)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rosters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                season INTEGER NOT NULL,
                roster_status TEXT DEFAULT 'active',
                FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                UNIQUE(player_id, team_id, season)
            )
        """)

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


def add_player(
    name: str,
    vitals: dict[str, Any],
    position: str,
    number: str,
    stats: list[dict[str, Any]],
    zones: list[dict[str, Any]],
    ratings: list[dict[str, Any]],
    traits: list[dict[str, Any]],
    season: int = 2026,
) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        # Insert player document
        cursor.execute(
            """
            INSERT INTO players (name, vitals, position, number, stats, zones, ratings, traits)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                json.dumps(vitals),
                position,
                number,
                json.dumps(stats),
                json.dumps(zones),
                json.dumps(ratings),
                json.dumps(traits),
            ),
        )
        player_id = cursor.lastrowid

        # Relate player to team in the junction table
        team_name = vitals.get("team")
        if team_name:
            team_id = get_or_create_team(cursor, team_name)
            cursor.execute(
                """
                INSERT OR REPLACE INTO rosters (player_id, team_id, season, roster_status)
                VALUES (?, ?, ?, 'active')
                """,
                (player_id, team_id, season),
            )

        return player_id


def get_team_roster(
    team_name: str, season: int = 2026
) -> list[dict[str, Any]]:
    """Instant B-tree lookup for all active players on a team."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT p.*
            FROM players p
            JOIN rosters r ON p.id = r.player_id
            JOIN teams t ON r.team_id = t.id
            WHERE t.name = ? 
              AND r.season = ? 
              AND r.roster_status = 'active'
            ORDER BY p.name ASC
            """,
            (team_name, season),
        )

        return [_row_to_dict(row) for row in cursor.fetchall()]


def get_player(player_id: int) -> Optional[Player]:
    """Fetches a player by ID and hydrates them into a domain Player object."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        row = cursor.fetchone()
        if not row:
            return None

        raw_data = _row_to_dict(row)
        return Player.from_db(raw_data)

def get_team_roster_players(
    team_name: str, season: int = 2026
) -> list[Player]:
    """Fetch active players for a team and hydrate them into domain Player objects."""
    raw_players = get_team_roster(team_name, season)
    return [Player.from_db(p) for p in raw_players]


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
    else:
        print("Player ID 2 not found.")