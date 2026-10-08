# ⚾ MLB Baseball Simulation

A deterministic Major League Baseball simulation engine featuring Statcast aerodynamics, 2D Bivariate Gaussian command variance, count leverage sequencing, and hybrid SQLite/JSON player persistence.

---

## 🚀 Architecture: Python Backend ↔ Expo Client

This repository is the **authoritative simulation backend** and also vendors the **React Native Expo client** under `frontend/`. The Flask REST API runs on port `5000`; the Expo web client runs on `8081`.

```text
[ frontend/ — Expo client ]                 [ backend — this repo ]
  assets/  React Native Expo                  main.py  →  Python Flask
  (Web / iOS / Android, port 8081)            (REST API, port 5000)
            │                                          │
            └────────── HTTP REST (CORS enabled) ──────┘
                                     │
                                     ├──► [ Statcast 2D Engine ]
                                     │      Bivariate Gaussian execution,
                                     │      count strategy, pitch sequencing
                                     │
                                     └──► [ SQLite Data Layer ]
                                            mlb.db: rosters, ratings, arsenals
```

`frontend/` is the full Expo client (scoreboard, strike zone, pitch selection, at-bat feed, and the Gameday Dev Menu), wired to this Python backend.

---

## 🛠 Quickstart Guide

### 1. Backend: Set Up Python Environment & Run

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Initialize & seed SQLite database (Yankees & Mets rosters)
python backend/database/seed.py --fresh

# 4. Start Flask REST API server (also serves a minimal page at /)
python main.py
```

Backend runs on `http://localhost:5000`. Health check: `curl http://localhost:5000/api/health`.

### 2. Client: Run the Expo Web Frontend

```bash
cd frontend/assets
npm install
npx expo start --web
```

- Web interface opens at `http://localhost:8081`.
- In the client header, open **`[🛠 GAMEDAY DEV MENU]`** (or press `Shift+D`).
- Use the **Backend Switcher Pill** to toggle between **`PYTHON FLASK (5000)`** (live) and **`MOCK ENGINE`**.

### 3. One Command: Boot Both Together

The vendored client lives at `frontend/assets`, so the root dev script starts both servers and shuts them down cleanly on `Ctrl+C`:

```bash
./dev.sh
# or
npm run dev
```

The client directory has an equivalent script that finds the backend one level up:

```bash
cd frontend && npm run dev
```

### 4. Run the Test Suite Concurrently

```bash
./run_tests.sh
# or using pytest with auto worker detection:
pytest -n auto tests/
```

---

## 📡 REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check & active game status |
| `GET` | `/api/state` | Full game state, active batter/pitcher, lineups & rotations |
| `POST`| `/api/start_game` | Initializes a new 9-inning game instance |
| `POST`| `/api/pitch` | Executes a single pitch with 2D Gaussian math & returns `Gameday2DPitchPacket` |
| `POST`| `/api/sim_at_bat` | Fast-forwards current at-bat to completion |
| `POST`| `/api/reset` | Resets game state and reloads fresh rosters from SQLite |
| `POST`| `/api/swap_lineup`| Swaps batting order positions |
| `POST`| `/api/swap_rotation`| Swaps starting pitcher rotation order |
| `GET` | `/api/rosters` | Returns hydrated rosters for both teams |

---

## 📁 Repository Layout

```text
baseball/
├── main.py                      # Flask entrypoint (port 5000)
├── dev.sh                       # boots backend + frontend/assets
├── backend/
│   ├── api/                     # Flask app factory, REST routes
│   ├── database/                # SQLite schema, seed, hydration
│   ├── engine/                  # Statcast + pitching/at-bat engines
│   ├── models/                  # Player models
│   └── mock/                    # mock_baseball_db.json seed data
├── tests/                       # consolidated pytest suites
├── templates/ + static/         # minimal Flask-served page
└── frontend/                    # vendored Expo client
    ├── assets/                  # Expo app root (scoreboard, strike zone, pitch UI)
    │   └── static/              # static resources (images, fonts, app icon)
    ├── docs/                    # pitching-logic physics spec
    └── dev.sh                   # client dev script (backend is one level up)
```

---

## 📚 Technical Documentation

In-repo notes:

- 📄 [Directory refactor note](docs/9-3-26_directory_refactor)
- 📄 [Pitch calculation notes](docs/pitch_calc.txt)
- 📄 [Pitcher intent vs execution](docs/pitcher_intent_vs_execution)

The vendored client carries the richer, interactive documentation under `frontend/docs/` (including the pitching-logic physics sandbox) and its own `frontend/README.md`.
