import argparse
from pathlib import Path
import sys

# Ensure repository root is on sys.path for direct script execution
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database.db import DB_PATH, add_player, init_db

# Baseline player data payloads
JUDGE_SEED_DATA = {
    "name": "Aaron Judge",
    "position": "RF",
    "number": "99",
    "vitals": {
        "age": 34,
        "experience": 10,
        "height": "6'7\"",
        "weight": 282,
        "bats": "R",
        "throws": "R",
        "team": "New York Yankees",
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
        {"category": "Fielding", "rating": 85},
    ],
    "traits": [
        {
            "name": "Home Run Threat",
            "tier": "Diamond",
            "description": "Elite exit velocity",
        }
    ],
}

MCLEAN_SEED_DATA = {
    "name": "Nolan McLean",
    "position": "SP",
    "number": "26",
    "vitals": {
        "age": 25,
        "experience": 2,
        "height": "6'2\"",
        "weight": 214,
        "bats": "R",
        "throws": "R",
        "team": "New York Mets",
    },
    "stats": [
        {
            "season": 2025,
            "w": 5,
            "l": 1,
            "era": 2.84,
            "so": 57,
            "whip": 1.08,
        },
        {
            "season": 2026,
            "w": 10,
            "l": 8,
            "era": 3.06,
            "so": 172,
            "whip": 1.12,
        },
    ],
    "zones": [
        {"zone": "low-away", "slugging": 0.190},
        {"zone": "upper-in", "slugging": 0.280},
    ],
    "ratings": [
        {"category": "Break", "rating": 99},
        {"category": "Velocity", "rating": 95},
        {"category": "Whiff", "rating": 91},
        {"category": "Ground Ball", "rating": 88},
        {"category": "Control", "rating": 66},
        {"category": "Stamina", "rating": 82},
        {"category": "Arm Strength", "rating": 97},
    ],
    "traits": [
        {
            "name": "3300 RPM Hammer",
            "tier": "Diamond",
            "description": (
                "Historic curveball spin generating 40%+ whiff rates and late"
                " two-plane drop."
            ),
        },
        {
            "name": "Wipeout Sweeper",
            "tier": "Diamond",
            "description": (
                "3,000 RPM frisbee sweep with massive horizontal glove-side"
                " run."
            ),
        },
        {
            "name": "Turbo Sinker",
            "tier": "Gold",
            "description": (
                "Mid-to-high 90s two-seamer that smothers launch angles into"
                " ground balls."
            ),
        },
        {
            "name": "Wild Card",
            "tier": "Bronze",
            "description": (
                "Elevated walk tendency in deep counts when chasing whiffs out"
                " of the zone."
            ),
        },
        {
            "name": "Two-Way Heritage",
            "tier": "Silver",
            "description": (
                "Collegiate two-way pedigree with 80-grade raw power if used"
                " as a pinch-hitter."
            ),
        },
    ],
}

PLAYERS_SEED_DATA = [JUDGE_SEED_DATA, MCLEAN_SEED_DATA]

def reset_database() -> None:
    """Removes the existing SQLite binary and sidecar journal/WAL files."""
    for ext in ["", "-wal", "-shm", "-journal"]:
        file_target = Path(f"{DB_PATH}{ext}")
        if file_target.exists():
            file_target.unlink()
            print(f"Removed: {file_target.name}")


def run_seed(fresh: bool = False, season: int = 2026) -> None:
    if fresh:
        print("Performing full database reset...")
        reset_database()

    print("Initializing database schema...")
    init_db()

    print(f"Seeding {len(PLAYERS_SEED_DATA)} players for season {season}...")
    for data in PLAYERS_SEED_DATA:
        player_id, is_created = add_player(**data, season=season)
        action = "Added" if is_created else "Updated"
        print(f"  + {action} [{player_id}] {data['name']} ({data['position']}) -> {data['vitals']['team']}")

    print("Database seeding completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the baseball simulation database.")
    parser.add_argument(
        "--fresh",
        "--reset",
        action="store_true",
        dest="fresh",
        help="Wipe the existing SQLite file and rebuild schema from scratch.",
    )
    parser.add_argument(
        "--season",
        type=int,
        default=2026,
        help="Target season year for roster linking (default: 2026).",
    )

    args = parser.parse_args()
    run_seed(fresh=args.fresh, season=args.season)