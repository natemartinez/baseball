import json
import sqlite3
from typing import Any

DB_PATH = "backend/database/mlb.db"


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
) -> list[dict[str, Any]]: # Expecting a team string -> returning a list of objects (players)
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

        rows = cursor.fetchall()
        return [
            {
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
            for row in rows
        ]

'''
nolan_data = {
    "name": "Nolan McLean",
    "position": "SP",
    "number": "26",
    "vitals": {
        "age": 25,
        "experience": 2,
        "height": "6'2\"",
        "weight": 214,
        "team": "New York Mets",
    },
    # If tracking his pitching metrics (since he transitioned full-time to the mound):
    "stats": [
        {"season": 2025, "w": 5, "l": 1, "era": 2.84, "so": 57, "whip": 1.08},
        {"season": 2026, "w": 10, "l": 8, "era": 3.06, "so": 172, "whip": 1.12},
    ],
    # Slugging allowed across pitch locations
    "zones": [
        {"zone": "low-away", "slugging": 0.190},
        {"zone": "upper-in", "slugging": 0.280},
    ],
    "ratings": [
        {"category": "Break", "rating": 99},
        {"category": "Velocity", "rating": 98},
        {"category": "Arm Strength", "rating": 97},
        {"category": "Control", "rating": 68},
        {"category": "Stamina", "rating": 78},
    ],
    "traits": [
        {
            "name": "Spin Monster Sweeper",
            "tier": "Diamond",
            "description": "Elite 3,000+ RPM horizontal sweep with extreme whiff rates",
        },
        {
            "name": "Power Fastball",
            "tier": "Gold",
            "description": "Mid-to-high 90s heater with heavy arm-side run from a low slot",
        },
        {
            "name": "Two-Way Heritage",
            "tier": "Silver",
            "description": "Former collegiate two-way star possessing 80-grade raw hitting power",
        },
    ],
}

judge_data = {
    "name": "Aaron Judge",
    "position": "RF",
    "number": "99",
    "vitals": {
        "age": 34,
        "experience": 10,
        "height": "6'7\"",
        "weight": 282,
        "team": "New York Yankees",  # <-- The function detects this
    },
    "stats": [
        {"season": 2024, "hr": 58, "rbi": 144, "avg": 0.322, "ops": 1.159},
        {"season": 2025, "hr": 45, "rbi": 115, "avg": 0.301, "ops": 1.050},
    ],
    "zones": [
        {"zone": "upper-in", "slugging": 0.650},
        {"zone": "heart", "slugging": 0.820},
    ],
    "ratings": [
        {"category": "Power", "rating": 99},
        {"category": "Contact", "rating": 88},
    ],
    "traits": [
        {
            "name": "Home Run Threat",
            "tier": "Diamond",
            "description": "Elite exit velocity",
        }
    ],
}


'''

#init_db()

#player_id = add_player(**nolan_data, season=2026)
judge = get_team_roster("New York Yankees") # Aaron Judge - Only Yankee in database
mclean = get_team_roster("New York Mets")  # Nolan Mclean - Only Met in database
print(f"Received Yankee: {judge}")
print(f"Received Met: {mclean}")