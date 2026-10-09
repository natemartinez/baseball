# ⚾ Project Roadmap & Maintenance Tracker

> **Core Purpose**: Eliminate context loss between development sessions. Keep this file updated at the end of each session so you can resume instantly without wondering "where was I?".

---

## ⚡ Session Resume Anchor (Where We Left Off)

| Key | Current Value |
| :--- | :--- |
| **Last Updated** | October 1, 2026 |
| **Active Phase** | **Phase 1: Interactive Frontend Dev Build & Python Backend Integration** |
| **Current Focus** | Building visual workbench with Debug Menu to replace terminal test loops |
| **Active Branches** | `main` |
| **Authoritative Backend** | Python `backend/` (`engine/game_engine.py`, `database/`) |
| **Test Suites Covered** | `tests/test_pitching_engine.py`, `tests/test_at_bat.py`, `tests/test_player_hydration.py`, `tests/test_statcast_engine.py` |

### 🎯 Last Completed Work
- [x] Verified Python authoritative backend:
  - Flask API already implemented in `backend/api/app.py` & `routes.py` (runs via `python main.py` on port `5000`).
  - Endpoints matching frontend contract: `/api/health`, `/api/state`, `/api/start_game`, `/api/pitch`, `/api/sim_at_bat`, `/api/reset`, `/api/swap_lineup`, `/api/rosters`.
  - All 4 consolidated test suites organized in `tests/` and passing 100% concurrently via `./run_tests.sh` / `pytest -n auto tests`: `tests/test_pitching_engine.py`, `tests/test_at_bat.py`, `tests/test_player_hydration.py`, and `tests/test_statcast_engine.py`.
- [x] Vendored `Baseball-Simulation-Client` into `frontend/` (`frontend/app/` is the Expo app):
  - Updated `GameRepository.ts` to default to `http://localhost:5000` for seamless connection to the Python Flask backend.
  - Built-in Gameday Dev Menu & Calibration Suite (`Shift+D` or tap `DEV`).

### 🚧 In-Progress Work
- [ ] Running the interactive frontend dev client (`frontend/app/`) against the live Python backend (`http://localhost:5000`).
- [ ] Verifying Dev Menu calibration controls (tweaking pitch intent, custom coordinates, at-bat outcomes) live on screen.

### 🚀 Immediate Next Steps (Pick up here next session!)
1. **[ ] Launch the Dev Pair**:
   - One command: `./dev.sh` (or `npm run dev`) boots backend + Expo web together.
   - Or manually — Terminal 1: `.venv/bin/python main.py` (backend, port 5000)
   - Terminal 2: `cd frontend/app && npx expo start --web` (Expo web, port 8081)
2. **[ ] Switch to Live Mode in UI**: Tap `DEV` or press `Shift+D` in the frontend, verify `isMockMode` is toggled to Live Backend (`http://localhost:5000`).
3. **[ ] Calibrate Visually**: Throw pitches and simulate at-bats from the UI, observing live Statcast physics and zone resolution without needing to re-run test scripts in the terminal!

---

## 🛠️ Quick-Start Sanity Commands (Zero Friction Resume)

When returning after a pause, run this single command to boot everything:

```bash
# ⚡ ONE COMMAND: Boots Python backend + Expo web frontend together:
./dev.sh
# (or `npm run dev`)
# -> Python backend starts on http://localhost:5000
# -> Expo Web frontend opens at http://localhost:8081
# -> Pressing Ctrl+C cleanly stops both servers!
# (The client is vendored at frontend/app)

# Alternatively, manual separate terminals:
# Terminal 1: .venv/bin/python main.py
# Terminal 2: cd frontend/app && npx expo start --web
# 2. Sanity Health Check (Optional)
curl -s http://localhost:5000/api/health
# -> {"active_game":false,"engine":"python-statcast-v4.8","port":5000,"status":"ok"}

# 3. Run Python baseline test suite concurrently in terminal
./run_tests.sh
# or via pytest directly:
pytest -n auto tests/
# or run individually:
.venv/bin/python tests/test_statcast_engine.py
.venv/bin/python tests/test_pitching_engine.py
.venv/bin/python tests/test_at_bat.py
.venv/bin/python tests/test_player_hydration.py
```

---

## 🗺️ Phased Evolution Roadmap

```
Phase 1: Interactive Dev Workbench  ──>  Phase 2: Full Inning & Game Loop  ──>  Phase 3: Rosters & Bullpen
           [ACTIVE FOCUS]                             [PLANNED]                         [PLANNED]
                  │                                          │                                 │
                  ▼                                          ▼                                 ▼
Phase 4: Trajectory & Spray Visuals  ──>  Phase 5: Box Scores & Season Mode  ──>  Phase 6: Live Statcast Ingestion
```

---

### Phase 1: Interactive Frontend Dev Build & Python Integration (🚧 ACTIVE)
*Goal: Replace terminal-only test runs with an interactive visual workbench where you can calibrate physics, pitching strategy, at-bat outcomes, and player hydration live on screen.*

- [ ] **Python Backend API Layer**:
  - [ ] Set up lightweight REST endpoints (e.g. FastAPI) wrapping `game_engine.py` and `database/`.
  - [ ] Implement CORS and JSON serialization for engine state.
- [ ] **Frontend $\leftrightarrow$ Backend Integration**:
  - [ ] Configure `HttpGameService.ts` to call the Python backend API.
  - [ ] Support fast switching between Python Live API and in-client Mock mode.
- [ ] **Visual Debug Menu & Calibration Harness**:
  - [ ] **Statcast Visualizer**: Display pitch trajectory crosshairs, 13-zone coordinates, velocity, spin, and aerodynamic break vectors (`test_statcast_enigne.py`).
  - [ ] **Strategy & Arsenal Inspector**: Visually test pitch selection weights across counts (`0-2`, `3-1`, etc.) and game leverage (`test_pitching_engine.py`).
  - [ ] **At-Bat Outcome Simulator**: Interactively trigger swings/takes, contact quality, and result feeds (`test_at_bat.py`).
  - [ ] **Player Hydration Inspector**: View and edit player attributes, pitch repertoires, and hot/cold zones loaded from DB (`test_player_hydration.py`).

---

### Phase 2: Full Inning & Game Loop State Machine (📋 Planned)
*Goal: Evolve from single pitch/at-bat testing into a complete baseball game loop.*

- [ ] **Inning State Machine**:
  - [ ] 3 outs tracking $\rightarrow$ clear count & bases $\rightarrow$ switch top/bottom half $\rightarrow$ advance batting order.
  - [ ] 9-inning game regulation, extra innings, walk-off conditions.
- [ ] **Baserunner Advancement Model**:
  - [ ] Force plays, groundouts, flyouts, and tag-ups.
  - [ ] Double play logic (6-4-3, 4-6-3) with runners on base.
  - [ ] Extra bases on gap hits and runner scoring from 2B/3B.
- [ ] **Batted Ball Exit Velocity (EV) & Launch Angle (LA)**:
  - [ ] Statcast hit classifications: Ground ball, Line drive, Fly ball, Pop-up.
  - [ ] Spray direction (Pull, Center, Opposite field).

---

### Phase 3: Roster Depth, Bullpen & Tactical Management (📋 Planned)
*Goal: Support full team rosters, pitching rotations, and managerial tactical choices.*

- [ ] **9-Man Batting Order & Lineup Cycling**:
  - [ ] Persistent lineup tracking across innings.
  - [ ] Bench players and pinch hitters.
- [ ] **Bullpen & Pitcher Stamina**:
  - [ ] Pitch count accumulation, fatigue curves, and velocity drops.
  - [ ] Warm-up mechanics and pitching changes.
  - [ ] Platoon splits (Right vs Left).
- [ ] **Tactical Management**:
  - [ ] Defensive shifts (Pull shift, Infield in, Double play depth).
  - [ ] Play calls (Bunt, Hit & Run, Intentional walk).

---

### Phase 4: Trajectory Visuals, Field Spray Charts & Sensory Polish (📋 Planned)
*Goal: Broadcast-style presentation with animated ball flight and field action.*

- [ ] 2D/3D pitch flight paths from pitcher's hand to strike zone.
- [ ] Field spray chart showing landing spots and defensive fielding plays.
- [ ] Sound effects (bat crack, ball in glove, umpire calls) and mobile haptics.

---

### Phase 5: Persistence, Box Scores & Season Simulation (📋 Planned)
*Goal: Career stats, historical game ledgers, and multi-game seasons.*

- [ ] MLB-style line scores and box scores (R, H, E).
- [ ] Complete pitch-by-pitch event ledger.
- [ ] Season schedules, team standings, and cumulative stat tracking (AVG, OBP, SLG, ERA, WHIP, WAR).

---

### Phase 6: Multiplayer & Live MLB Statcast Feeds (🔮 Future Vision)
*Goal: Real-time head-to-head play and real-world MLB data integration.*

- [ ] Real-time WebSocket pitcher vs batter duels.
- [ ] Direct import of MLB Statcast Savant profiles for real MLB players.

---

## 🏛️ Architectural Decisions Log (ADRs)

| Date | Decision | Context & Rationale | Status |
| :--- | :--- | :--- | :--- |
| **2026-10** | **Python as Authoritative Backend** | The Python codebase (`backend/`) contains the true simulation engine (`game_engine.py`) and database layer. All core simulation logic lives here. | **Accepted** |
| **2026-10** | **Remove `server.js` prototype** | `server.js`/`db.js` were a temporary, monolithic Node prototype. Removed from `frontend/`; the Flask Python API in this repo is authoritative. | **Done** |
| **2026-10** | **Frontend Dev Build as Interactive Test Harness** | Instead of constantly running terminal unit tests (`pytest`), the frontend with its built-in Debug Menu serves as a visual, real-time calibration harness for the 4 engine domains. | **Accepted** |
| **2026-09** | **13-Zone Coordinate Model** | 9 inner zones + 4 chase corridors allow discrete count leverage and batter vulnerability matrices. | **Accepted** |
| **2026-09** | **Bivariate Gaussian Jitter** | Miss displacement scaled by pitcher control rating for Statcast-grade command dispersion. | **Accepted** |

---

## 🧠 The "Anti-Amnesia" Pause & Resume Protocol

### 🛑 When You're Pausing (Takes 2 minutes)
1. **Update the Session Resume Anchor** at the top:
   - Check off what you completed under **Last Completed Work**.
   - Write the exact **1 to 3 tasks** you need to do next under **Immediate Next Steps**.
2. **Note Any Gotchas**:
   - Add a bullet under **Known Quirks & Tech Debt** if something is half-finished or broken.
3. **Commit or Stash**:
   ```bash
   git status
   git commit -m "wip: <concise summary of session progress>"
   ```

### 🟢 When You're Resuming (Takes 2 minutes)
1. Open [logs/TODO.md](logs/TODO.md).
2. Read the **Session Resume Anchor** at the top.
3. Run the **Quick-Start Sanity Commands** to confirm everything boots.
4. Jump straight into task #1 under **Immediate Next Steps**.

---

## ⚠️ Known Quirks & Tech Debt

- **Node prototype removed**: the old standalone `server.js`/`db.js` client prototype (and the native Android app) were removed from `frontend/`. All engine logic stays in the Python `backend/`.
- **Backend Port**: The Python Flask backend runs on port `5000` (the Node prototype used `3000`). The Expo client defaults to `http://localhost:5000` on web.
- **Android Emulator Loopback**: Remember Android emulators use `http://10.0.2.2:5000` to reach `localhost:5000` on the host machine.

