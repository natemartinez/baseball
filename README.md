# ⚾ MLB Baseball Simulation

A deterministic Major League Baseball simulation engine featuring Statcast aerodynamics, count leverage sequencing, and hybrid SQLite/JSON player persistence.

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

For the current 3D field, camera, strike-zone projection, and pitch-visualization design, see:
📖 [**docs/08_3D_FIELD_PITCH_AND_HUD.md**](docs/08_3D_FIELD_PITCH_AND_HUD.md)

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

### 2. Run Test Suite Concurrently
Run all consolidated test suites in parallel:
```bash
./scripts/run_tests.sh
# or using pytest with auto worker detection:
pytest -n auto tests/
```

### 3. Connect the React Native Expo Client
Boot the Flask backend and the vendored Expo client together:
```bash
./scripts/dev.sh
# or: npm run dev
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

- 📄 [**Documentation index**](docs/README.md)
- 📄 [**3D Field, Pitch Visualization & HUD**](docs/08_3D_FIELD_PITCH_AND_HUD.md) — coordinates, camera, projected HUD, mock pitch flow, and IVB kinematics
- Additional architecture, API-contract, data-schema, and state-machine documents are planned and tracked in the documentation index.
