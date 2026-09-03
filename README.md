# Baseball Simulation

A baseball simulation game built in Python as a side project exploring game logic, software architecture, and probability modeling.

The core focus is dialing in the fundamental battle of baseball: **The At-Bat** — the strategic chess match between Pitcher/Catcher vs. Batter, resolved step-by-step using Statcast-inspired probability weights. The backend is powered by a SQLite database running a hybrid relational/JSON pipeline that feeds data into the simulation engine.

---

## What It Does Right Now

- **Core At-Bat Engine:** Simulates the pitch sequence from intent to outcome:
  - Pitch selection based on count and strategy
  - Batter anticipation and swing decisions (take, chase, swing)
  - Pitcher execution vs. missed spots in the zone
  - Contact checks and batted-ball resolution (exit velocity, launch angle, hit/out outcomes)
- **Hybrid SQLite Database:**
  - Relational `teams` and `players` tables linked via an indexed `rosters` junction table for fast, season-specific lookups.
  - Flexible JSON storage for deep player metrics: pitch/swing zones, attribute ratings, badges/traits, and multi-year stats.
- **Test Matchup Seeded:**
  - The database is populated with full test profiles for **Aaron Judge** (NYY) and **Nolan McLean** (NYM) to validate the engine before scaling up to full rosters.

---

## Sample Player Output

Example data payloads returned from the database layer (`get_team_roster()`):

### Aaron Judge (New York Yankees)
```json
[
  {
    "id": 1,
    "name": "Aaron Judge",
    "position": "RF",
    "number": "99",
    "vitals": {
      "age": 34,
      "experience": 10,
      "height": "6'7\"",
      "weight": 282,
      "team": "New York Yankees"
    },
    "stats": [
      {"season": 2024, "hr": 58, "rbi": 144, "avg": 0.322, "ops": 1.159},
      {"season": 2025, "hr": 45, "rbi": 115, "avg": 0.301, "ops": 1.050}
    ],
    "zones": [
      {"zone": "upper-in", "slugging": 0.650},
      {"zone": "heart", "slugging": 0.820}
    ],
    "ratings": [
      {"category": "Power", "rating": 99},
      {"category": "Contact", "rating": 88}
    ],
    "traits": [
      {
        "name": "Home Run Threat",
        "tier": "Diamond",
        "description": "Elite exit velocity"
      }
    ]
  }
]
```

### Nolan McLean (New York Mets)
```json
[
  {
    "id": 2,
    "name": "Nolan McLean",
    "position": "SP",
    "number": "26",
    "vitals": {
      "age": 25,
      "experience": 2,
      "height": "6'2\"",
      "weight": 214,
      "team": "New York Mets"
    },
    "stats": [
      {"season": 2025, "w": 5, "l": 1, "era": 2.84, "so": 57, "whip": 1.08},
      {"season": 2026, "w": 10, "l": 8, "era": 3.06, "so": 172, "whip": 1.12}
    ],
    "zones": [
      {"zone": "low-away", "slugging": 0.190},
      {"zone": "upper-in", "slugging": 0.280}
    ],
    "ratings": [
      {"category": "Break", "rating": 99},
      {"category": "Velocity", "rating": 98},
      {"category": "Arm Strength", "rating": 97},
      {"category": "Control", "rating": 68},
      {"category": "Stamina", "rating": 78}
    ],
    "traits": [
      {
        "name": "Spin Monster Sweeper",
        "tier": "Diamond",
        "description": "Elite 3,000+ RPM horizontal sweep with extreme whiff rates"
      },
      {
        "name": "Power Fastball",
        "tier": "Gold",
        "description": "Mid-to-high 90s heater with heavy arm-side run from a low slot"
      },
      {
        "name": "Two-Way Heritage",
        "tier": "Silver",
        "description": "Former collegiate two-way star possessing 80-grade raw hitting power"
      }
    ]
  }
]
```

---

## Data Flow & Architecture

The system decouples database queries from simulation logic to keep the engine fast and modular:

```text
[ SQLite (players.db) ]
        │  1. SELECT row & json.loads()
        ▼
[ Data Access Layer (db.py) ]
        │  2. Raw Python dict
        ▼
[ Domain Models (player.py) ]  ──►  [ Simulation Engine (game_engine.py) ]
        │                                  │
        │                                  ▼
[ API / Transport (main.py) ]  ◄──  Simulation Event Log (JSON)
        │
        ▼  3. HTTP / WebSocket
[ Client (static/templates or SPA) ]
```

- **`players.db`:** Stores raw relational records and serialized JSON attributes.
- **`db.py`:** Runs SQL queries and decodes JSON into Python dicts.
- **`player.py`:** Wraps raw dicts into typed `Player` objects with helper methods (`get_rating()`, `has_trait()`).
- **`game_engine.py`:** Runs at-bat probability logic on `Player` objects and outputs an event log.
- **`main.py`:** Orchestrates requests between the database, engine, and network.
- **Client:** Receives the event log to render strike zone graphics and box scores.

---

## What's Coming

- Populating full 26-man and 40-man rosters for the Mets and Yankees
- Inning state machine: baserunning, outs, runs, and a full 9-inning game loop
- Bullpen management, substitutions, and pitcher fatigue
- Connecting the API (`main.py`) to the frontend (`static/`, `templates/`) to render interactive pitch zones, ball flight, and live box scores

---

## Project Structure

```text
baseball/
├── backend/
│   ├── database/
│   │   ├── schema.sql           # Table definitions, junction tables, and indexes
│   │   ├── db.py                # Database connection and CRUD operations
│   │   └── players.db           # SQLite database (gitignored)
│   ├── batter_strategy.py       # Batter anticipation and swing logic
│   ├── pitch_strategy.py        # Pitch selection and location targeting
│   ├── strike_zone.py           # Coordinate mapping and zone checks
│   └── game_engine.py           # Core at-bat loop and probability calculations
├── main.py                      # Application entry point / server
├── roster.py                    # Roster configuration and lineup management
├── static/                      # Frontend assets (CSS, JS, graphics)
├── templates/                   # Frontend HTML templates
└── logs/
    ├── may_2026_dev_log.md      # Early menu & lineup prototype notes
    └── aug_2026_dev_log.md      # At-bat loop & SQLite architecture notes
```

---

*Built as a learning project — tracking progress, architectural decisions, and dev history in `logs/`.*
