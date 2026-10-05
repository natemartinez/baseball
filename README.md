# ⚾ MLB Baseball Simulation

A deterministic Major League Baseball simulation engine featuring Statcast aerodynamics, 2D Bivariate Gaussian command variance, count leverage sequencing, and hybrid SQLite/JSON player persistence.

---

## 🚀 Unified Architecture: Python Backend <-> React Native Client

This repository powers the authoritative simulation backend and connects directly with the modern React Native Expo mobile & web client.

```text
[ React Native Expo Client ] (Port 8081: Web / iOS / Android)
            │
            ▼ HTTP REST (CORS enabled)
[ Python Flask Backend ] (Port 5000: main.py)
            │
            ├──► [ Statcast 2D Engine ] (Bivariate Gaussian execution, count strategy)
            │
            └──► [ SQLite Data Layer ] (mlb.db: rosters, ratings, pitch arsenals)
```

For full architectural history, contract schemas, and integration details, see:
📖 [**docs/07_FRONTEND_BACKEND_ALIGNMENT.md**](docs/07_FRONTEND_BACKEND_ALIGNMENT.md)

---

## 🛠 Quickstart Guide

### 1. Set Up Python Environment & Run Backend
```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Initialize & seed SQLite database (Yankees & Mets rosters)
python backend/database/seed.py --fresh

# 4. Start Flask REST API server
python main.py
```
Backend runs on `http://0.0.0.0:5000`.

### 2. Connect the React Native Expo Client
In the client repository (`Baseball-Simulation-Client`):
```bash
cd mobile
npx expo start --web
```
- Open `http://localhost:8081` in your browser.
- In the client header, open **`[🛠 GAMEDAY DEV MENU]`**.
- Use the **Backend Switcher Pill** to toggle between **`PYTHON FLASK (5000)`** and **`MOCK ENGINE`**.

---

## 📡 REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check & active game status |
| `GET` | `/api/state` | Returns full game state, active batter/pitcher, lineups & rotations |
| `POST`| `/api/start_game` | Initializes a new 9-inning game instance |
| `POST`| `/api/pitch` | Executes a single pitch with 2D Gaussian math & returns `Gameday2DPitchPacket` |
| `POST`| `/api/sim_at_bat` | Fast-forwards current at-bat to completion |
| `POST`| `/api/reset` | Resets game state and reloads fresh rosters from SQLite |
| `POST`| `/api/swap_lineup`| Swaps batting order positions |
| `POST`| `/api/swap_rotation`| Swaps starting pitcher rotation order |

---

## 📚 Technical Documentation

- 📄 [**00. Architecture Overview**](docs/00_ARCHITECTURE_OVERVIEW.md)
- 📄 [**01. Data Schema & SQLite Tables**](docs/01_DATA_SCHEMA.md)
- 📄 [**02. API Contracts & TypeScript Interfaces**](docs/02_API_CONTRACTS.md)
- 📄 [**03. State Machines & Inning Loop**](docs/03_STATE_MACHINES.md)
- 📄 [**04. Game Loop Tick**](docs/04_GAME_LOOP_TICK.md)
- 📄 [**05. Dev Test Harness**](docs/05_DEV_TEST_HARNESS.md)
- 📄 [**06. Statcast 2D Physics & Calibration**](docs/06_STATCAST_2D_PHYSICS.md)
- 📄 [**07. Frontend <-> Backend Realignment**](docs/07_FRONTEND_BACKEND_ALIGNMENT.md)
